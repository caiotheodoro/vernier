import { useCallback, useMemo, useRef, useState } from "react";
import { useData } from "./data/load";
import { RowsClient, type RowsStatus } from "./data/rows";
import { HF_DATASET_URL, REPO_URL, SOURCE_DATASET_URL, repoFile, type Stats } from "./data/types";
import { int } from "./lib/format";
import { applySlice } from "./state/slice";
import { parseHash, useHash, type SliceState } from "./state/url";
import { Coverage } from "./views/Coverage";
import { Filters } from "./views/Filters";
import { Frame } from "./views/Frame";
import { Grid } from "./views/Grid";
import { Health } from "./views/Health";
import { Quality } from "./views/Quality";
import { Scale } from "./views/Scale";

export function App(): JSX.Element {
  const data = useData();
  const hash = useHash();
  const state: SliceState = useMemo(() => parseHash(hash), [hash]);
  const [rowsStatus, setRowsStatus] = useState<RowsStatus>("idle");
  const gridRef = useRef<HTMLDivElement>(null);

  const scrollToGrid = useCallback(() => {
    gridRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  if (data.status === "loading") {
    return (
      <main className="page">
        <p className="grid-empty">Loading the measurement…</p>
      </main>
    );
  }
  if (data.status === "error") {
    return (
      <main className="page">
        <p className="grid-empty">
          The measurement data did not load ({data.message}). Reload the page, or read the numbers directly in{" "}
          <a className="footer-link" href={repoFile("MEASUREMENT_CARD.json")}>
            MEASUREMENT_CARD.json
          </a>
          .
        </p>
      </main>
    );
  }

  const { stats, frames } = data;
  return <Loaded stats={stats} frames={frames} state={state} rowsStatus={rowsStatus} setRowsStatus={setRowsStatus} gridRef={gridRef} scrollToGrid={scrollToGrid} />;
}

type LoadedProps = {
  stats: Stats;
  frames: import("./data/types").Frame[];
  state: SliceState;
  rowsStatus: RowsStatus;
  setRowsStatus: (s: RowsStatus) => void;
  gridRef: React.RefObject<HTMLDivElement>;
  scrollToGrid: () => void;
};

function Loaded({ stats, frames, state, rowsStatus, setRowsStatus, gridRef, scrollToGrid }: LoadedProps): JSX.Element {
  const rows = useMemo(
    () => new RowsClient(stats.rows_api.dataset, stats.rows_api.config, stats.rows_api.split),
    [stats.rows_api.dataset, stats.rows_api.config, stats.rows_api.split],
  );
  const shown = useMemo(() => applySlice(frames, state), [frames, state]);
  const selected = state.f ? (frames.find((f) => f.id === state.f) ?? null) : null;

  return (
    <>
      <a className="skip" href="#filters">
        Skip to the filters
      </a>
      <main className="page">
        <header className="masthead">
          <h1 className="wordmark">vernier</h1>
          <p className="masthead-meta">
            <a className="footer-link" href={SOURCE_DATASET_URL}>
              {stats.generated_from.dataset}
            </a>{" "}
            · {int(30000)} frames · judge {stats.generated_from.judge} {stats.generated_from.prompt_variant}
          </p>
        </header>

        {rowsStatus === "slow" || rowsStatus === "down" ? (
          <p className="notice">
            {rowsStatus === "slow"
              ? "Hugging Face's dataset server is rate-limiting this page, so frames arrive slowly. Labels and statistics are already here."
              : "Frames are loading from Hugging Face's dataset server and it did not answer. Labels and statistics still work."}
          </p>
        ) : null}

        <Scale stats={stats} frames={frames} state={state} onReason={scrollToGrid} />

        <Filters stats={stats} state={state} shown={shown.length} total={frames.length} />

        <div ref={gridRef}>
          <Grid frames={shown} stats={stats} state={state} rows={rows} onStatus={setRowsStatus} />
        </div>

        {selected ? <Frame frame={selected} stats={stats} state={state} rows={rows} /> : null}

        <Quality stats={stats} state={state} onFilter={scrollToGrid} />
        <Coverage stats={stats} state={state} />
        <Health stats={stats} />

        <footer className="footer">
          <p>
            Statistics PPI++, Gwet AC1, bootstrap ·{" "}
            <a className="footer-link" href={repoFile("src/vernier/estimation/ppi.py")}>
              estimation
            </a>{" "}
            · Judge {stats.generated_from.judge_rev} on Modal vLLM ·{" "}
            <a className="footer-link" href={repoFile("docs/ETHICS.md")}>
              {int(stats.thumbnails.n)} frames shipped, the rest fetched live
            </a>{" "}
            · Method pre-registered,{" "}
            <a className="footer-link" href={repoFile("docs/DECISIONS.md")}>
              {stats.repo.n_decisions} logged decisions
            </a>{" "}
            · Code{" "}
            <a className="footer-link" href={REPO_URL}>
              {stats.repo.n_tests} tests, mypy strict
            </a>{" "}
            ·{" "}
            <a className="footer-link" href={repoFile("MEASUREMENT_CARD.json")}>
              MEASUREMENT_CARD.json
            </a>{" "}
            ·{" "}
            <a className="footer-link" href={HF_DATASET_URL}>
              the data
            </a>
          </p>
          <p>
            One rater, n {stats.generated_from.n_rater_labels}. No frame is redistributed. Built from{" "}
            {stats.generated_from.card_digest.slice(0, 19)}…
          </p>
        </footer>
      </main>
    </>
  );
}
