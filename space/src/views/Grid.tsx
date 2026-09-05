// The frame grid, in three tiers.
//
// The tiers are not a loading concession, they are the shape of the licence. 24 frames ship with
// this page and paint instantly from one atlas. Everything else lives on Hugging Face's dataset
// server, which costs ~10 seconds per call whatever you ask it for -- so this grid never fetches
// an image on its own. A tile with no local thumbnail draws the judge's complete output instead,
// which is real data rather than a placeholder, and one image is fetched only when a reader
// opens a frame.
import { useCallback, useEffect, useMemo, useRef } from "react";
import type { Frame, Hands, Stats, Task } from "../data/types";
import { useAtlas, useWidth, cssToken } from "../lib/hooks";
import { agrees, judgeHands, judgeManipulation, raterBinary } from "../state/slice";
import { update, type SliceState } from "../state/url";

type Props = { frames: Frame[]; stats: Stats; state: SliceState };

const GAP = 10;
const RATIO = 9 / 16;
const MIN_TILE = 150;

/** Ships locally · fetched on request · human-judged but not ours to ship. */
export type Tier = "local" | "remote" | "withheld";

export function tierOf(frame: Frame): Tier {
  if (frame.t) return "local";
  return frame.r ? "withheld" : "remote";
}

const BAND: { tier: Tier; title: string; blurb: (n: number) => string }[] = [
  {
    tier: "local",
    title: "Held locally",
    blurb: () => "Shipped with this page, from Build AI's own Apache-2.0 release. No network.",
  },
  {
    tier: "withheld",
    title: "Human-judged, not ours to ship",
    blurb: (n) =>
      `${n} frames a rater labelled that this repository does not republish — Ego4D's licence, ` +
      "EPIC's non-commercial terms, or someone other than the camera wearer is in shot. " +
      "Hugging Face serves the picture; open one to fetch it.",
  },
  {
    tier: "remote",
    title: "On request",
    blurb: () => "The judge's own output is below each id. Open a frame to fetch its picture.",
  },
];

function columnsFor(width: number): number {
  if (width < 420) return 2;
  if (width < 700) return 3;
  if (width < 1000) return 5;
  return 6;
}

/** Judge and rater answers as shape, not colour alone: strokes for hands, a square for yes/no. */
function drawGlyph(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  colour: string,
  task: Task,
  hands: Hands | null,
  manip: boolean | null,
): void {
  ctx.save();
  ctx.strokeStyle = colour;
  ctx.fillStyle = colour;
  ctx.lineWidth = 2;
  if (task === "manipulation") {
    if (manip === null) {
      ctx.setLineDash([2, 2]);
      ctx.strokeRect(x + 0.5, y - 8.5, 8, 8);
    } else if (manip) {
      ctx.fillRect(x, y - 9, 9, 9);
    } else {
      ctx.strokeRect(x + 0.5, y - 8.5, 8, 8);
    }
  } else if (hands === null) {
    ctx.setLineDash([2, 2]);
    ctx.beginPath();
    ctx.moveTo(x + 1, y);
    ctx.lineTo(x + 9, y);
    ctx.stroke();
  } else if (hands === 0) {
    ctx.beginPath();
    ctx.arc(x + 5, y - 5, 3.5, 0, Math.PI * 2);
    ctx.stroke();
  } else {
    for (let i = 0; i < hands; i += 1) {
      ctx.beginPath();
      ctx.moveTo(x + 1 + i * 5, y);
      ctx.lineTo(x + 1 + i * 5, y - 10);
      ctx.stroke();
    }
  }
  ctx.restore();
}

export function Grid({ frames, stats, state }: Props): JSX.Element {
  const atlas = useAtlas(stats);
  const bands = useMemo(() => {
    const by: Record<Tier, Frame[]> = { local: [], withheld: [], remote: [] };
    for (const f of frames) by[tierOf(f)].push(f);
    return by;
  }, [frames]);

  if (frames.length === 0) {
    return (
      <p className="grid-empty">
        No frames match. Loosen a filter, or open the link you were sent again.
      </p>
    );
  }

  return (
    <div className="grid-bands">
      {BAND.map(({ tier, title, blurb }) =>
        bands[tier].length === 0 ? null : (
          <section className="band" key={tier} data-fade data-delay="2">
            <p className="eyebrow">
              {title} <span className="count-pill">{bands[tier].length}</span>
            </p>
            <p className="band-blurb">{blurb(bands[tier].length)}</p>
            <Band frames={bands[tier]} stats={stats} state={state} atlas={atlas} tier={tier} />
          </section>
        ),
      )}
      <p className="legend">
        <span className="legend-judge">judge</span>
        <span className="legend-rater">rater</span>
        <span>outline: judge and rater disagree</span>
        <span>hollow dot: the judge hesitated (confidence below .99)</span>
      </p>
    </div>
  );
}

function Band({
  frames,
  stats,
  state,
  atlas,
  tier,
}: Props & { atlas: ImageBitmap | null; tier: Tier }): JSX.Element {
  const [wrapRef, width] = useWidth<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cols = columnsFor(width);
  const tileW = width > 0 ? Math.max(MIN_TILE, Math.floor((width - GAP * (cols - 1)) / cols)) : MIN_TILE;
  const tileH = Math.round(tileW * RATIO);
  const rows = Math.ceil(frames.length / cols);
  const totalH = rows * (tileH + GAP);

  const select = useCallback(
    (id: string | null) => update(state, { f: id }),
    [state],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || width <= 0) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(totalH * dpr)) {
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(totalH * dpr);
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const bg = cssToken("--bg") || "#ffffff";
    const subtle = cssToken("--bg-subtle") || "#f8f8f7";
    const codeBg = cssToken("--code-bg") || "#f3f3ed";
    const border = cssToken("--border") || "#e8e8e4";
    const ink = cssToken("--ink") || "#171717";
    const muted = cssToken("--muted") || "#6b6b6b";
    const accent = cssToken("--v-measured") || "#c93d1e";
    const mono = '11px "Geist Mono", ui-monospace, monospace';

    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, width, totalH);

    frames.forEach((frame, i) => {
      const x = (i % cols) * (tileW + GAP);
      const y = Math.floor(i / cols) * (tileH + GAP);

      if (frame.t && atlas) {
        ctx.fillStyle = subtle;
        ctx.fillRect(x, y, tileW, tileH);
        const scale = Math.min(tileW / frame.t.w, tileH / frame.t.h);
        const dw = frame.t.w * scale;
        const dh = frame.t.h * scale;
        ctx.drawImage(
          atlas,
          frame.t.x,
          frame.t.y,
          frame.t.w,
          frame.t.h,
          x + (tileW - dw) / 2,
          y + (tileH - dh) / 2,
          dw,
          dh,
        );
      } else {
        // Not a placeholder: the judge's complete answer, with the `---` it wrote as a rule.
        ctx.fillStyle = codeBg;
        ctx.fillRect(x, y, tileW, tileH);
        ctx.strokeStyle = border;
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 0.5, y + 0.5, tileW - 1, tileH - 1);

        ctx.font = mono;
        ctx.textAlign = "left";
        ctx.fillStyle = muted;
        ctx.fillText(frame.id.slice(0, 8), x + 10, y + 19);

        // The rater's answer sits opposite the id rather than under the judge's, where it
        // collided with both the second output line and the glyph row.
        if (tier === "withheld" && frame.r) {
          ctx.fillStyle = accent;
          ctx.fillRect(x, y, 2, tileH);
          ctx.textAlign = "right";
          ctx.fillText(`rater ${raterBinary(frame, state.task) ? "yes" : "no"}`, x + tileW - 10, y + 19);
          ctx.textAlign = "left";
        }

        const parts = frame.q.raw.split(/\n-+\n/);
        ctx.fillStyle = ink;
        ctx.font = '13px "Geist Mono", ui-monospace, monospace';
        ctx.fillText((parts[0] ?? "").trim().slice(0, 12), x + 10, y + 46);
        ctx.strokeStyle = border;
        ctx.beginPath();
        ctx.moveTo(x + 10, y + 55.5);
        ctx.lineTo(x + Math.min(52, tileW - 20), y + 55.5);
        ctx.stroke();
        ctx.fillText((parts[1] ?? "").trim().slice(0, 12), x + 10, y + 74);
      }

      drawGlyph(ctx, x + 8, y + tileH - 8, ink, state.task, judgeHands(frame, state.src), judgeManipulation(frame, state.src));
      if (frame.r) {
        drawGlyph(ctx, x + 26, y + tileH - 8, accent, state.task, frame.r.h, frame.r.m);
      }
      // Only the 33 frames the judge hesitated on get a mark. A tick on all 600 said nothing.
      if (frame.q.c !== null && frame.q.c < 0.99) {
        ctx.strokeStyle = accent;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(x + tileW - 11, y + 11, 3.5, 0, Math.PI * 2);
        ctx.stroke();
      }
      if (agrees(frame, state.task, state.src) === false) {
        ctx.strokeStyle = accent;
        ctx.lineWidth = 2;
        ctx.strokeRect(x + 1, y + 1, tileW - 2, tileH - 2);
      }
      if (frame.id === state.f) {
        ctx.strokeStyle = ink;
        ctx.lineWidth = 3;
        ctx.strokeRect(x + 1.5, y + 1.5, tileW - 3, tileH - 3);
      }
    });
  }, [frames, atlas, width, tileW, tileH, cols, totalH, state.task, state.src, state.f, tier]);

  const onClick = (e: React.MouseEvent<HTMLCanvasElement>): void => {
    const box = e.currentTarget.getBoundingClientRect();
    const c = Math.floor((e.clientX - box.left) / (tileW + GAP));
    const r = Math.floor((e.clientY - box.top) / (tileH + GAP));
    if (c < 0 || c >= cols) return;
    const frame = frames[r * cols + c];
    if (frame) select(frame.id === state.f ? null : frame.id);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLCanvasElement>): void => {
    const current = state.f ? frames.findIndex((f) => f.id === state.f) : -1;
    const step: Record<string, number> = {
      ArrowRight: 1,
      ArrowLeft: -1,
      ArrowDown: cols,
      ArrowUp: -cols,
      PageDown: cols * 4,
      PageUp: -cols * 4,
    };
    if (e.key in step) {
      e.preventDefault();
      const next = current < 0 ? 0 : Math.min(frames.length - 1, Math.max(0, current + (step[e.key] ?? 0)));
      const frame = frames[next];
      if (frame) select(frame.id);
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      const frame = frames[e.key === "Home" ? 0 : frames.length - 1];
      if (frame) select(frame.id);
    } else if (e.key === "Escape") {
      select(null);
    }
  };

  const selected = state.f ? frames.findIndex((f) => f.id === state.f) : -1;

  return (
    <div className="grid-wrap" ref={wrapRef}>
      <canvas
        className="grid-canvas"
        ref={canvasRef}
        style={{ height: `${totalH}px` }}
        tabIndex={0}
        role="listbox"
        aria-label={`${frames.length} frames, ${stats.generated_from.judge} ${stats.generated_from.prompt_variant}`}
        aria-activedescendant={selected >= 0 ? `tile-${state.f}` : undefined}
        onClick={onClick}
        onKeyDown={onKeyDown}
      />
      {/* Every frame in this band, not the first 200: aria-activedescendant must always resolve. */}
      <ul className="grid-a11y">
        {frames.map((f) => (
          <li key={f.id} id={`tile-${f.id}`} role="option" aria-selected={f.id === state.f}>
            {f.corpus} {f.id.slice(0, 8)} judge {String(judgeHands(f, state.src) ?? "—")} hands,{" "}
            {String(judgeManipulation(f, state.src) ?? "—")} manipulation
            {f.r ? `, rater ${String(raterBinary(f, state.task))}` : ", no rater label"}
            {f.t ? ", held locally" : ", picture on request"}
          </li>
        ))}
      </ul>
    </div>
  );
}
