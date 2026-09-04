import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Frame, Hands, Stats, Task } from "../data/types";
import { ImageCache, RowsClient, type RowsStatus } from "../data/rows";
import { useWidth } from "../lib/hooks";
import { agrees, judgeHands, judgeManipulation, raterBinary } from "../state/slice";
import { update, type SliceState } from "../state/url";
import { cssToken } from "../lib/hooks";

type Props = {
  frames: Frame[];
  stats: Stats;
  state: SliceState;
  rows: RowsClient;
  onStatus: (s: RowsStatus) => void;
};

const GAP = 8;
const RATIO = 3 / 4; // tile height / width
const MIN_TILE = 132;

function columnsFor(width: number): number {
  if (width < 420) return 2;
  if (width < 700) return 4;
  if (width < 1000) return 6;
  return 8;
}

/** Draw the judge's and rater's answers as shape, not colour alone: hands are 0/1/2 strokes,
 *  manipulation is a filled (yes) or hollow (no) square. */
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
  } else {
    const n = hands ?? 0;
    if (hands === null) {
      ctx.setLineDash([2, 2]);
      ctx.beginPath();
      ctx.moveTo(x + 1, y);
      ctx.lineTo(x + 9, y);
      ctx.stroke();
    } else {
      for (let i = 0; i < Math.max(n, 0); i += 1) {
        ctx.beginPath();
        ctx.moveTo(x + 1 + i * 5, y);
        ctx.lineTo(x + 1 + i * 5, y - 10);
        ctx.stroke();
      }
      if (n === 0) {
        ctx.beginPath();
        ctx.arc(x + 5, y - 5, 3.5, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }
  ctx.restore();
}

export function Grid({ frames, stats, state, rows, onStatus }: Props): JSX.Element {
  const [wrapRef, width] = useWidth<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [scrollY, setScrollY] = useState(0);
  const [, forceRender] = useState(0);

  const cols = columnsFor(width);
  const tileW = width > 0 ? Math.max(MIN_TILE, Math.floor((width - GAP * (cols - 1)) / cols)) : MIN_TILE;
  const tileH = Math.round(tileW * RATIO);
  const rowsCount = Math.ceil(frames.length / cols);
  const totalH = rowsCount * (tileH + GAP);

  const images = useMemo(() => new ImageCache(rows, () => tileW), [rows, tileW]);
  useEffect(() => images.onChange(() => forceRender((n) => n + 1)), [images]);
  useEffect(() => rows.onStatus(onStatus), [rows, onStatus]);

  useEffect(() => {
    const onScroll = (): void => setScrollY(window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const select = useCallback(
    (id: string | null) => {
      update(state, { f: id });
    },
    [state],
  );

  // Draw: only the rows intersecting the viewport, plus one screen of prefetch.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || width <= 0) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const box = canvas.getBoundingClientRect();
    const viewTop = Math.max(0, -box.top);
    const viewH = window.innerHeight;

    const firstRow = Math.max(0, Math.floor((viewTop - tileH) / (tileH + GAP)));
    const lastRow = Math.min(rowsCount - 1, Math.ceil((viewTop + viewH) / (tileH + GAP)));
    const prefetchLast = Math.min(rowsCount - 1, lastRow + Math.ceil(viewH / (tileH + GAP)));

    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(totalH * dpr)) {
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(totalH * dpr);
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const ground = cssToken("--ground") || "#dde3e8";
    const panel = cssToken("--panel") || "#f4f6f8";
    const rule = cssToken("--rule") || "rgba(85,99,111,.4)";
    const steel = cssToken("--steel") || "#55636f";
    const signal = cssToken("--signal") || "#e8591c";
    const human = cssToken("--human") || "#2d6a9f";

    ctx.fillStyle = ground;
    ctx.fillRect(0, 0, width, totalH);

    const visibleRows: number[] = [];
    const aheadRows: number[] = [];

    for (let r = firstRow; r <= prefetchLast; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const i = r * cols + c;
        const frame = frames[i];
        if (!frame) continue;
        const prio = r <= lastRow ? 0 : 1;
        (prio === 0 ? visibleRows : aheadRows).push(frame.row);
        images.request(frame.id, frame.row, prio);
        if (r > lastRow) continue;

        const x = c * (tileW + GAP);
        const y = r * (tileH + GAP);

        ctx.fillStyle = panel;
        ctx.fillRect(x, y, tileW, tileH);

        const entry = images.get(frame.id);
        if (entry?.state === "ready") {
          const b = entry.bitmap;
          const scale = Math.min(tileW / b.width, tileH / b.height);
          const dw = b.width * scale;
          const dh = b.height * scale;
          ctx.drawImage(b, x + (tileW - dw) / 2, y + (tileH - dh) / 2, dw, dh);
        } else {
          ctx.strokeStyle = rule;
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, tileW - 1, tileH - 1);
        }

        const jh = judgeHands(frame, state.src);
        const jm = judgeManipulation(frame, state.src);
        drawGlyph(ctx, x + 6, y + tileH - 6, signal, state.task, jh, jm);
        if (frame.r) {
          drawGlyph(ctx, x + 24, y + tileH - 6, human, state.task, frame.r.h, frame.r.m);
        }

        if (frame.q.c !== null) {
          const len = Math.max(2, Math.round(frame.q.c * (tileH - 12)));
          ctx.strokeStyle = steel;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(x + tileW - 4, y + tileH - 6);
          ctx.lineTo(x + tileW - 4, y + tileH - 6 - len);
          ctx.stroke();
        }

        if (agrees(frame, state.task, state.src) === false) {
          ctx.strokeStyle = signal;
          ctx.lineWidth = 2;
          ctx.strokeRect(x + 1, y + 1, tileW - 2, tileH - 2);
        }

        if (frame.id === state.f) {
          ctx.strokeStyle = cssToken("--ink") || "#161a1e";
          ctx.lineWidth = 3;
          ctx.strokeRect(x + 1.5, y + 1.5, tileW - 3, tileH - 3);
        }
      }
    }

    images.prefetchRows([...visibleRows, ...aheadRows]);
  }, [frames, images, width, tileW, tileH, cols, rowsCount, totalH, state.task, state.src, state.f, scrollY]);

  const onClick = (e: React.MouseEvent<HTMLCanvasElement>): void => {
    const box = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - box.left;
    const y = e.clientY - box.top;
    const c = Math.floor(x / (tileW + GAP));
    const r = Math.floor(y / (tileH + GAP));
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
      const delta = step[e.key] ?? 0;
      const next = current < 0 ? 0 : Math.min(frames.length - 1, Math.max(0, current + delta));
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

  if (frames.length === 0) {
    return (
      <p className="grid-empty">
        No frames match. Loosen a filter, or open the link you were sent again.
      </p>
    );
  }

  const selectedIndex = state.f ? frames.findIndex((f) => f.id === state.f) : -1;

  return (
    <div className="grid-wrap" ref={wrapRef}>
      <canvas
        className="grid-canvas"
        ref={canvasRef}
        style={{ height: `${totalH}px` }}
        tabIndex={0}
        role="listbox"
        aria-label={`${frames.length} frames, ${stats.generated_from.judge} ${stats.generated_from.prompt_variant}`}
        aria-activedescendant={selectedIndex >= 0 ? `tile-${state.f}` : undefined}
        onClick={onClick}
        onKeyDown={onKeyDown}
      />
      <ul className="grid-a11y">
        {frames.slice(0, 200).map((f) => (
          <li key={f.id} id={`tile-${f.id}`} role="option" aria-selected={f.id === state.f}>
            {f.corpus} {f.id.slice(0, 8)} judge {String(judgeHands(f, state.src) ?? "—")} hands,{" "}
            {String(judgeManipulation(f, state.src) ?? "—")} manipulation
            {f.r ? `, rater ${String(raterBinary(f, state.task))}` : ", no rater label"}
          </li>
        ))}
      </ul>
      <p className="legend">
        <span className="legend-signal">judge</span>
        <span className="legend-human">rater</span>
        <span>outline: judge and rater disagree</span>
        <span>right edge: judge confidence</span>
      </p>
    </div>
  );
}
