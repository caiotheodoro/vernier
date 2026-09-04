import { useEffect, useState } from "react";
import type { Frame as FrameRow, Stats } from "../data/types";
import { CORPUS_LABEL } from "../data/types";
import { RowsClient } from "../data/rows";
import { conf } from "../lib/format";
import { update, type SliceState } from "../state/url";
import { repoFile } from "../data/types";

type Props = { frame: FrameRow; stats: Stats; state: SliceState; rows: RowsClient };

function hands(h: number | null): string {
  return h === null ? "—" : String(h);
}

function manip(m: boolean | null): string {
  return m === null ? "—" : m ? "yes" : "no";
}

export function Frame({ frame, stats, state, rows }: Props): JSX.Element {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setSrc(null);
    setFailed(false);
    void rows
      .resolveOne(frame.row)
      .then((info) => {
        if (!cancelled) {
          if (info) setSrc(info.src);
          else setFailed(true);
        }
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [frame.row, rows]);

  const prov = stats.provenance[frame.r ? "h4" : "gold_sets"];

  return (
    <section className="detail" aria-live="polite" aria-label="selected frame">
      <div className="detail-image">
        {src && !failed ? (
          <img
            className="detail-img"
            src={src}
            width={frame.w}
            height={frame.h}
            alt={`Frame ${frame.id} from ${CORPUS_LABEL[frame.corpus]}`}
            onError={() => {
              void rows.refresh(frame.row).then((info) => (info ? setSrc(info.src) : setFailed(true)));
            }}
          />
        ) : (
          <p className="panel-note">
            {failed
              ? "This frame is served by Hugging Face's dataset server and it did not answer. The labels below still apply."
              : "Loading the frame from Hugging Face…"}
          </p>
        )}
      </div>
      <div className="detail-body">
        <button type="button" className="button detail-close" onClick={() => update(state, { f: null })}>
          close
        </button>
        <table className="detail-table">
          <thead>
            <tr>
              <th className="detail-th">source</th>
              <th className="detail-th">hands</th>
              <th className="detail-th">manipulation</th>
              <th className="detail-th">confidence</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="detail-td">
                {stats.generated_from.judge} {stats.generated_from.prompt_variant}
              </td>
              <td className="detail-td">{hands(frame.q.h)}</td>
              <td className="detail-td">{manip(frame.q.m)}</td>
              <td className="detail-td">{conf(frame.q.c)}</td>
            </tr>
            <tr>
              <td className="detail-td">gemini stored</td>
              <td className="detail-td">{frame.g ? hands(frame.g.h) : "—"}</td>
              <td className="detail-td">{frame.g ? manip(frame.g.m) : "—"}</td>
              <td className="detail-td">—</td>
            </tr>
            <tr className="detail-row-rater">
              <td className="detail-td">rater</td>
              <td className="detail-td">{frame.r ? hands(frame.r.h) : "—"}</td>
              <td className="detail-td">{frame.r ? manip(frame.r.m) : "—"}</td>
              <td className="detail-td">{frame.r ? frame.r.d : "—"}</td>
            </tr>
          </tbody>
        </table>

        {frame.r?.note ? <p className="detail-note">“{frame.r.note}”</p> : null}
        {!frame.r ? <p className="detail-note">Not in the 93-frame human-gold set.</p> : null}
        {frame.q.s !== "ok" ? (
          <p className="detail-note">The judge's answer could not be parsed: status {frame.q.s}.</p>
        ) : null}

        <p className="detail-meta">
          {frame.id} · {CORPUS_LABEL[frame.corpus]} · {frame.w}×{frame.h} · row {frame.row}
        </p>
        {prov ? (
          <p className="detail-meta">
            how this row was made →{" "}
            <a className="footer-link" href={repoFile("MEASUREMENT_CARD.json")}>
              {prov.claim_ref}
            </a>{" "}
            ·{" "}
            <a className="footer-link" href={repoFile("docs/DECISIONS.md")}>
              {prov.decision}
            </a>
          </p>
        ) : null}
      </div>
    </section>
  );
}
