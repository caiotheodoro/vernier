// datasets-server client: resolves a frame's `row` to an image URL at runtime. Images are
// never cached anywhere the Space serves from (docs/ETHICS.md section 4); the browser
// holds decoded bitmaps in memory for the session only.
//
// /rows?dataset=...&config=default&split=train&offset=<row>&length=<n>, length <= 100.
// `image.src` is a signed cached-asset URL that expires: a 4xx on the image fetch refreshes
// that row's window once, never in a loop. In-flight /rows calls are capped at 3; image
// decodes (createImageBitmap, off the main thread) at 6.

export type RowInfo = { src: string; width: number; height: number; frameId: string };

type RowsResponse = {
  rows: { row_idx: number; row: { frame_id: string; image: { src: string; height: number; width: number } } }[];
};

const MAX_WINDOW = 100;
const MAX_ROWS_IN_FLIGHT = 3;
const MAX_DECODES_IN_FLIGHT = 6;

class Semaphore {
  private active = 0;
  private waiting: (() => void)[] = [];
  constructor(private readonly limit: number) {}
  async acquire(): Promise<void> {
    if (this.active < this.limit) {
      this.active += 1;
      return;
    }
    await new Promise<void>((resolve) => this.waiting.push(resolve));
    this.active += 1;
  }
  release(): void {
    this.active -= 1;
    const next = this.waiting.shift();
    if (next) next();
  }
}

export type RowsStatus = "idle" | "ok" | "down";

export class RowsClient {
  private readonly cache = new Map<number, RowInfo>();
  private readonly pending = new Map<number, Promise<RowInfo | null>>();
  private readonly gate = new Semaphore(MAX_ROWS_IN_FLIGHT);
  private status: RowsStatus = "idle";
  private readonly listeners = new Set<(s: RowsStatus) => void>();

  constructor(
    private readonly dataset: string,
    private readonly config: string,
    private readonly split: string,
  ) {}

  onStatus(cb: (s: RowsStatus) => void): () => void {
    this.listeners.add(cb);
    cb(this.status);
    return () => this.listeners.delete(cb);
  }

  getStatus(): RowsStatus {
    return this.status;
  }

  private setStatus(s: RowsStatus): void {
    if (s === this.status) return;
    this.status = s;
    for (const cb of this.listeners) cb(s);
  }

  /** Coalesce a set of rows into windows of at most MAX_WINDOW consecutive offsets. */
  static windows(rows: number[]): { offset: number; length: number }[] {
    const sorted = [...new Set(rows)].sort((a, b) => a - b);
    const out: { offset: number; length: number }[] = [];
    let start = -1;
    let end = -1;
    for (const r of sorted) {
      if (start < 0) {
        start = r;
        end = r;
      } else if (r - start + 1 <= MAX_WINDOW) {
        end = r;
      } else {
        out.push({ offset: start, length: end - start + 1 });
        start = r;
        end = r;
      }
    }
    if (start >= 0) out.push({ offset: start, length: end - start + 1 });
    return out;
  }

  private url(offset: number, length: number): string {
    const p = new URLSearchParams({
      dataset: this.dataset,
      config: this.config,
      split: this.split,
      offset: String(offset),
      length: String(length),
    });
    return `https://datasets-server.huggingface.co/rows?${p.toString()}`;
  }

  private async fetchWindow(offset: number, length: number): Promise<void> {
    await this.gate.acquire();
    try {
      const res = await fetch(this.url(offset, length), { headers: { accept: "application/json" } });
      if (!res.ok) throw new Error(`rows HTTP ${res.status}`);
      const body = (await res.json()) as RowsResponse;
      for (const entry of body.rows) {
        this.cache.set(entry.row_idx, {
          src: entry.row.image.src,
          width: entry.row.image.width,
          height: entry.row.image.height,
          frameId: entry.row.frame_id,
        });
      }
      this.setStatus("ok");
    } catch (err) {
      this.setStatus("down");
      throw err;
    } finally {
      this.gate.release();
    }
  }

  /** Resolve many rows at once; missing ones are fetched in coalesced windows. */
  resolve(rows: number[]): Promise<RowInfo | null>[] {
    const missing = rows.filter((r) => !this.cache.has(r) && !this.pending.has(r));
    for (const w of RowsClient.windows(missing)) {
      const p = this.fetchWindow(w.offset, w.length);
      for (let r = w.offset; r < w.offset + w.length; r += 1) {
        if (!missing.includes(r)) continue;
        const one = p
          .then(() => this.cache.get(r) ?? null)
          .catch(() => null)
          .finally(() => this.pending.delete(r));
        this.pending.set(r, one);
      }
    }
    return rows.map((r) => {
      const hit = this.cache.get(r);
      if (hit) return Promise.resolve(hit);
      return this.pending.get(r) ?? Promise.resolve(null);
    });
  }

  async resolveOne(row: number): Promise<RowInfo | null> {
    const [p] = this.resolve([row]);
    return p ?? null;
  }

  /** Drop a row's cached (expired) URL and fetch its window again, once. */
  async refresh(row: number): Promise<RowInfo | null> {
    this.cache.delete(row);
    return this.resolveOne(row);
  }
}

export type ImageEntry =
  | { state: "loading" }
  | { state: "ready"; bitmap: ImageBitmap }
  | { state: "failed" };

/** Decoded tiles for the grid. Visible tiles are queued at priority 0, the next screen at 1. */
export class ImageCache {
  private readonly entries = new Map<string, ImageEntry>();
  private readonly queue: { id: string; row: number; prio: number; seq: number }[] = [];
  private readonly queued = new Set<string>();
  private seq = 0;
  private active = 0;
  private readonly listeners = new Set<() => void>();

  constructor(
    private readonly rows: RowsClient,
    private readonly tileWidth: () => number,
  ) {}

  onChange(cb: () => void): () => void {
    this.listeners.add(cb);
    return () => this.listeners.delete(cb);
  }

  get(id: string): ImageEntry | undefined {
    return this.entries.get(id);
  }

  request(id: string, row: number, prio: number): void {
    if (this.entries.has(id) || this.queued.has(id)) return;
    this.queued.add(id);
    this.queue.push({ id, row, prio, seq: this.seq++ });
    this.pump();
  }

  /** Warm the rows cache for a batch (one coalesced /rows call per window). */
  prefetchRows(rows: number[]): void {
    this.rows.resolve(rows);
  }

  private pump(): void {
    while (this.active < MAX_DECODES_IN_FLIGHT && this.queue.length > 0) {
      // Lowest priority value first; among equals, most recently requested first (the user
      // is looking there now).
      let best = 0;
      for (let i = 1; i < this.queue.length; i += 1) {
        const a = this.queue[i]!;
        const b = this.queue[best]!;
        if (a.prio < b.prio || (a.prio === b.prio && a.seq > b.seq)) best = i;
      }
      const [job] = this.queue.splice(best, 1);
      if (!job) break;
      this.active += 1;
      this.entries.set(job.id, { state: "loading" });
      void this.load(job.id, job.row).finally(() => {
        this.active -= 1;
        this.queued.delete(job.id);
        this.pump();
      });
    }
  }

  private notify(): void {
    for (const cb of this.listeners) cb();
  }

  private async fetchBitmap(info: RowInfo): Promise<ImageBitmap | "expired"> {
    const res = await fetch(info.src, { mode: "cors" });
    if (res.status >= 400 && res.status < 500) return "expired";
    if (!res.ok) throw new Error(`image HTTP ${res.status}`);
    const blob = await res.blob();
    const width = Math.max(64, Math.round(this.tileWidth() * Math.min(2, window.devicePixelRatio || 1)));
    return createImageBitmap(blob, { resizeWidth: Math.min(width, info.width), resizeQuality: "medium" });
  }

  private async load(id: string, row: number): Promise<void> {
    try {
      let info = await this.rows.resolveOne(row);
      if (!info) throw new Error("row unavailable");
      let bitmap = await this.fetchBitmap(info);
      if (bitmap === "expired") {
        info = await this.rows.refresh(row);
        if (!info) throw new Error("row unavailable after refresh");
        bitmap = await this.fetchBitmap(info);
        if (bitmap === "expired") throw new Error("image URL expired twice");
      }
      this.entries.set(id, { state: "ready", bitmap });
    } catch {
      this.entries.set(id, { state: "failed" });
    }
    this.notify();
  }
}
