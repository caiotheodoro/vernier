// Fetches the export's JSON once per page load, memoised. No numbers live anywhere else.
import { useEffect, useState } from "react";
import type { Frame, Stats } from "./types";

const base = import.meta.env.BASE_URL;

let statsPromise: Promise<Stats> | null = null;
let framesPromise: Promise<Frame[]> | null = null;

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${base}${path}`, { cache: "force-cache" });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function loadStats(): Promise<Stats> {
  statsPromise ??= getJson<Stats>("data/stats.json");
  return statsPromise;
}

export function loadFrames(): Promise<Frame[]> {
  framesPromise ??= getJson<Frame[]>("data/frames.json");
  return framesPromise;
}

export type Data =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; stats: Stats; frames: Frame[] };

export function useData(): Data {
  const [data, setData] = useState<Data>({ status: "loading" });
  useEffect(() => {
    let cancelled = false;
    Promise.all([loadStats(), loadFrames()])
      .then(([stats, frames]) => {
        if (!cancelled) setData({ status: "ready", stats, frames });
      })
      .catch((err: unknown) => {
        if (!cancelled) setData({ status: "error", message: err instanceof Error ? err.message : String(err) });
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return data;
}
