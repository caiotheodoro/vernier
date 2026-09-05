# vernier Space — spec for the builder

A static Hugging Face Space that lets someone look at Build AI's `Egocentric-10K-Evaluation`
frames, sliced by what the judge said, what the human said, and how confident the judge was —
with vernier's measured numbers (and their intervals) drawn as the thing you navigate by.

The job it does: answer "how good is this batch, and show me the frames that say so" without a
notebook. Every number on screen is a link to the frames behind it.

This is a product, not a demo. Latency, defaults, shareability and empty states are features.
Nothing here is decoration.

## Non-negotiables (from the repo's own rules)

- **Only the frames `docs/ETHICS.md` §4 names are republished** (D073): the 24 human-labelled
  Egocentric-10K frames with nobody but the camera wearer in shot, as one 256px atlas built by
  `scripts/export_space_thumbnails.py`. Every other frame -- including all Ego4D and
  EPIC-KITCHENS-100 frames -- loads at runtime from the HF datasets-server rows API and is
  never cached anywhere the Space serves from.
- **No transcribed numbers** (`AGENTS.md` rule 2). Every figure comes from a committed
  `data/*.json` via the export script below. No hand-typed percentages in TSX.
- **Judge is never the oracle** (`AGENTS.md` rule 3). Human labels are shown as ground truth;
  judge output is shown as the thing being measured. The UI must never label a judge answer
  "correct" — it says "agrees with rater" / "disagrees with rater".
- **Vendor numbers in ink, measurements in signal.** The published figure is a reference tick;
  what vernier measured is the colored thing. This is the visual argument of the whole page.

## Stack

- Vite + React 18 + TypeScript, strict. No UI kit, no Tailwind, no component library.
- One CSS file with custom properties (tokens below). No CSS-in-JS.
- Frame grid: a virtualized `<canvas>` grid (own implementation or `@tanstack/react-virtual`
  driving `<img>` tiles is acceptable; canvas preferred — the JD lists WebGL/custom renderers
  as nice-to-have, and a canvas grid that stays at 60fps with 10k tiles is the visible proof).
- Charts: hand-drawn SVG. No chart library. There are three chart types total (scale, bars,
  reliability); a library would cost more than it saves and look like every other dashboard.
- State: URL hash is the store. `useSyncExternalStore` over `location.hash`. No Redux.
- Build output: `space/dist/` → uploaded as the Space's root. Space `README.md` front matter:

  ```yaml
  ---
  title: vernier
  emoji: 📏
  sdk: static
  app_file: index.html
  pinned: false
  license: apache-2.0
  datasets:
    - builddotai/Egocentric-10K-Evaluation
  ---
  ```

  Listing the dataset in `datasets:` is what makes the Space appear on Build AI's dataset page.
  That routing matters more than any feature.

## Repo layout

```
space/
  SPEC.md              this file
  README.md            HF front matter + one paragraph
  index.html
  package.json  vite.config.ts  tsconfig.json
  src/
    main.tsx  App.tsx
    tokens.css
    state/url.ts       hash <-> SliceState
    data/
      types.ts         mirrors export schema below
      load.ts          fetches /data/*.json, memoised
      rows.ts          datasets-server client + image URL refresh
    views/
      Scale.tsx        the caliper hero
      Filters.tsx
      Grid.tsx         canvas grid
      Frame.tsx        selected-frame detail
      Quality.tsx      disagreement + reliability
      Coverage.tsx     per-corpus distributions
      Health.tsx       run status/latency/cost
    lib/
      wilson.ts        for on-the-fly proportions in the UI (n small)
  public/data/         written by scripts/export_space_data.py, committed
scripts/export_space_data.py   new; reads data/*.json, writes space/public/data/*.json
```

`make space-data` runs the export. `make space` builds. Add both to the Makefile in the same
style as the existing targets (one-line `##` help comment).

## Design tokens

```css
:root {
  --ground:  #DDE3E8;   /* page; photos read true on cool neutral mid-light */
  --panel:   #F4F6F8;   /* detail panel, filter bar */
  --ink:     #161A1E;   /* text, vendor/published figures, axis */
  --steel:   #55636F;   /* rules, ticks, secondary text */
  --signal:  #E8591C;   /* ONLY CI jaws, dots, tile outlines, glyphs. Never text: 2.8:1 on ground */
  --human:   #2D6A9F;   /* ONLY rater glyphs/marks. Never text: 4.4:1 on ground */
  --focus:   #161A1E;   /* 2px solid outline, offset 2px */

  --font: "Instrument Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --fs-display: 3.5rem;  --lh-display: 1.0;  --fw-display: 600;
  --fs-h2: 1.5rem;       --lh-h2: 1.2;
  --fs-body: 0.9375rem;  --lh-body: 1.5;
  --fs-data: 0.8125rem;  --lh-data: 1.3;   /* tabular-nums on, same family, not mono */

  --space-1: 4px; --space-2: 8px; --space-3: 16px; --space-4: 32px; --space-5: 64px;
  --measure: 68ch;
  --radius: 2px;   /* one value; tiles and buttons only. Panels are square. */
}
```

Load Instrument Sans from Google Fonts with `font-display: swap` and `font-variant-numeric:
tabular-nums` on every element that shows a number. No second family. No monospace. No
all-caps labels. No eyebrow labels above headings. No shadows. Rules (1px `--steel` at 40%
opacity) only where they separate strata, never as decoration.

Dark mode: none. The page is a light workshop surface; photos are the dark element. Say so in
a CSS comment so nobody adds it later.

## Layout

Left-aligned, single column, max width 1280px, gutters `--space-4`. Sections in this order;
the hero and the grid are the page, the rest are below the fold and reachable by in-page links.

```
vernier                             Egocentric-10K-Evaluation · 30,000 frames · judge qwen3-vl

Active manipulation, Egocentric-10K                      [task ▾] [corpus ▾]
published 91.7                       ▼
|----+----+----+----+----+----+----+----+----+----|
70                    80        [====●====]      92
                                 measured 80.8, 95% CI 70.1–91.6, n gold 33, n judged 200
                        3 frames where judge said yes and rater said no      open →

corpus ▾   judge answer ▾   rater answer ▾   agreement ▾   confidence ▾   [copy link]

┌────┬────┬────┬────┬────┬────┬────┬────┐   canvas grid, 8 across at 1280, 4 at 640
│    │    │    │    │    │    │    │    │   tile: frame; bottom-left two small marks
│    │    │    │    │    │    │    │    │   (signal = judge, human = rater) for hands
└────┴────┴────┴────┴────┴────┴────┴────┘   and manipulation; right edge: confidence
                                            as tick length

selected frame ───────────────────────────────────────────────────────────────
[ 1920×1080 ]   qwen3-vl P0b     hands 2   manipulation yes   confidence .9999
                gemini (stored)  hands 2   manipulation yes
                rater            hands 2   manipulation no    "holding, not working"
                how this row was made → MEASUREMENT_CARD.json claim H4 · D059

Quality ──────   Coverage ──────   Health ──────   (below the fold)
```

The one motion on the page: on load, the CI jaws start at the scale ends and close onto the
interval over 600ms, ease-out. `prefers-reduced-motion` → no animation, jaws render in place.
Nothing else moves without a user action. Selecting a tile expands the detail panel; that is
the only other transition (150ms height).

## Views

### 1. Scale (hero)

One task × one corpus at a time. Controls: task (`hand_count` shown as "at least one hand",
`hand_eq2` as "both hands", `manipulation` as "active manipulation"), corpus (three).

Draws a horizontal scale from `floor(min-5)` to `ceil(max+5)` over: published value (ink
triangle above the scale, label "published 91.7"), naive judge rate (small `--steel` tick,
label "judge alone 90.0"), PPI++ estimate with CI (signal jaws + dot). Under it, one sentence
in `--fs-data` naming n gold, n judged, and `why_not_clustered` verbatim when `clustered` is
false ("interval is a lower bound on true width: no participant id on these frames").

Below the sentence, up to three "reason links" derived from the current slice — the smallest
sets of frames that explain the gap:
- "N frames where judge said yes and rater said no" → sets grid filter `judge=yes&rater=no`
- "N frames where judge said no and rater said yes"
- "N frames the judge could not parse" (status != ok)

Where the published figure exists only for a task/corpus pair that vernier didn't measure with
gold, the scale shows published + judge-alone only and says "no human gold on this slice".

Data: `stats.json.ppi[corpus][task]`, `stats.json.published[corpus][task]`.

### 2. Filters

One row. Each control is a native `<select>` styled minimally (keyboard-first). Filters:
corpus, judge answer (hands 0/1/2, manipulation yes/no), rater answer (same, plus "unlabelled"),
agreement (agrees / disagrees / no rater), confidence (≥.99, .9–.99, <.9), judge (qwen3-vl /
gemini stored). "copy link" copies the current URL; the button text becomes "copied" for 1.5s.

Result count sits at the row's right edge: "412 of 600 frames" — always the denominator.

### 3. Grid

Canvas-drawn, virtualized, `devicePixelRatio`-aware. Rows of tiles at 4:3 ratio (frames are
16:9 or 1:1 depending on corpus — letterbox on `--panel`, never crop). Each tile shows:
- the image (loaded lazily; placeholder is the tile outline, not a spinner)
- bottom-left: two small glyphs — judge (signal) and rater (human) — for the active task.
  Hands: 0/1/2 as 0/1/2 short vertical strokes. Manipulation: filled square = yes, outline = no.
  Rater glyph absent when unlabelled.
- right edge: confidence as a tick whose length is `conf` × tile height, in `--steel`.
- disagreement: 2px `--signal` outline on the tile. That is the only outline.

Keyboard: arrows move selection, Enter opens detail, Escape closes, `/` focuses filters.
Selection is in the URL (`&f=<frame_id>`).

Perf budget: first paint < 1s on a cold load over the precomputed JSON; scroll at 60fps with
10,000 tiles in the index; images decode off-main-thread (`createImageBitmap`) with a
concurrency cap of 6; visible tiles first, then one screen ahead.

### 4. Frame detail

Full-width panel under the grid. Left: the frame at natural aspect, max 720px wide. Right: a
three-row table — qwen3-vl (P0b), gemini stored (P0b), rater — with hands, manipulation,
confidence, and the rater's `note` verbatim if present. Under the table: "how this row was
made" → link to the card claim id and DECISIONS entry (`stats.json.provenance`). Frame id and
`source_dataset` in `--fs-data`, selectable.

If the rater row is absent: "Not in the 93-frame human-gold set" and nothing else.

### 5. Quality

Two panels side by side at ≥900px, stacked below.

Left — **Disagreement**: a 3×3 (hands) and 2×2 (manipulation) confusion table, judge rows ×
rater columns, cells are counts and every cell is a button that sets the grid filter to that
cell. Under it: AC1 with its bootstrap CI and κ beside it, in one line, from
`stats.json.agreement`. Never the word "accuracy".

Right — **Confidence**: the reliability diagram from `stats.json.calibration[task]`, bins
drawn as SVG bars on the x-axis of confidence, bar height = accuracy, a diagonal in `--steel`.
Empty bins are drawn as empty outlines at zero height with their range — never omitted (the
repo's own calibration rule). The H7 finding — 99% of frames in one bin — becomes visible as
one bar and nine outlines. ECE in the caption. A one-line note: "Greedy decoding, temperature
0: confidence is near 1.0 almost everywhere by construction."

### 6. Coverage

Per corpus, two horizontal stacked bars from the 29,400 stored gemini labels: hands 0/1/2 and
manipulation yes/no, with the count on each segment. The published headline number is drawn
as an ink tick over the bar so a reader can see that "96.42%" is the 1+2 segment. Beside each
bar, vernier's measured PPI value and CI as a signal jaw at the same scale — same visual
grammar as the hero, smaller.

A fourth row, `Egocentric-100K-Evaluation`, appears only if `stats.json.corpora` contains it
(the export script emits it when `data/e2_100k*.json` exists). Until then the row is absent,
not "coming soon".

### 7. Health

From `stats.json.runs[]`: for each run (E2 P0a, E2 P0b, E5 ×8, gold sets ×3): n requested, n
ok, status counts, total cost, wall time, latency p50/p95/max. Latency as a strip plot of the
600 gold-set calls (the only per-call latencies committed). The 229-second outlier should be
visible as what it is — a preemption retry — with a hover label from the run's notes.

Cost per 10k frames as one sentence, computed in the export: "10,000 frames, both prompt arms:
$8.56, 10.7 h of judge time" (`e2_full_n10000.json`: P0a $4.47 / 5.6 h, P0b $4.09 / 5.1 h —
`total_latency_ms` is summed per-call latency, so label it judge time, not wall time).
Gold-set calls: p50 1.9 s, p95 3.3 s, max 229.5 s (n=600).

## Data export — `scripts/export_space_data.py`

Reads committed `data/*.json` and `MEASUREMENT_CARD.json`; writes `space/public/data/`.
Deterministic; running it twice is a no-op diff. Add a test that the export's numbers equal the
card's (same rule as `test_emit_card.py`).

### `frames.json` — the grid index (600 gold frames; optionally the 10k E10k-ego if per-frame
E2 responses are ever committed)

```ts
type Frame = {
  id: string;               // frame_id
  corpus: "egocentric-10k" | "ego4d" | "epic-kitchens-100";
  w: number; h: number;
  row: number;              // row index in the source parquet split, for the rows API
  q: { h: 0|1|2|null; m: boolean|null; c: number|null; s: "ok"|"unparseable"|"refused"|"timeout" };  // qwen3-vl P0b
  g: { h: 0|1|2; m: boolean } | null;   // gemini stored P0b
  r: { h: 0|1|2; m: boolean; d: "easy"|"medium"|"hard"; note: string|null } | null;  // rater primary
};
```

`row` is the offset of that `frame_id` in the datasets-server split. Compute it once in the
export by scanning the parquet's `frame_id` column (`scripts/check_eval_parquets.py` already
reads it); commit it. Without `row` the client cannot address a frame in the rows API without
a full scan.

Sources: `data/gold_judged/G200-*.P0b.json` (q), `data/rung1_stored_labels.json` (g, filter
by frame id), `data/labels/caio/primary.json` (r), `data/membership/G200-*.json` (corpus, w, h).

### `stats.json`

```ts
type Stats = {
  generated_from: { card_digest: string; git_rev: string };
  published: Record<Corpus, Record<Task, number>>;             // from PRE-REGISTRATION table, via emit_card's constants
  ppi: Record<Corpus, Record<"hand_count"|"manipulation", {
    naive: number; n_judged: number;
    value: number; lo: number; hi: number; n_gold: number; n_unlabelled: number;
    method: "ppi++"; clustered: boolean; why_not_clustered: string|null;
  }>>;                                                          // data/wave4_analysis.json.ppi
  agreement: {
    h4: Record<Task, { ac1: number; lo: number; hi: number; kappa: number; raw: number; n: number }>;
    intra_rater: Record<Task, { ac1: number; lo: number; hi: number; kappa: number; n_pairs: number }>;
  };
  calibration: Record<Task, { ece: number; n: number; bins: { lo: number; hi: number; n: number; mean_conf: number|null; accuracy: number|null }[] }>;
  coverage: Record<Corpus, { hands: [number, number, number]; manipulation: [number, number]; n: number }>;  // from stored gemini labels
  prompt_sweep: { hand_count: Record<string, number>; manipulation: Record<string, number>; n: number };     // e5_full_n2000.json
  runs: { id: string; n_requested: number; n_ok: number; status_counts: Record<string, number>; cost_usd: number; wall_ms: number; latency_ms?: number[] }[];
  provenance: Record<string, { claim_ref: string; decision: string }>;  // e.g. "h4" -> {"data/wave4_analysis.json#H4", "D059"}
  corpora: Corpus[];
};
```

Task labels for the UI live in one map in `types.ts`:
`hand_count → "at least one hand"`, `hand_eq2 → "both hands"`, `manipulation → "active manipulation"`.

## Rows API client — `src/data/rows.ts`

Endpoint: `https://datasets-server.huggingface.co/rows?dataset=builddotai/Egocentric-10K-Evaluation&config=default&split=train&offset=<row>&length=<n>`.
Columns: `frame_id` (string), `image` ({src, height, width}), `source_dataset` (string),
`hand_count` (int), `active_labor` ("yes"/"no"). 30,000 rows. Verify the exact
`source_dataset` values against `scripts/published_labels.py` before hardcoding any.

- `length` max is 100. Batch by contiguous `row` ranges from the visible tiles; coalesce.
- `image.src` is a cached-asset URL that **expires**. Treat a 4xx on image load as "refresh
  this row" and refetch its `/rows` window once; do not retry in a loop.
- No API key needed for this ungated dataset. If the request fails, the grid shows tile
  outlines with the frame id and a single line at the top: "Frames are loading from Hugging
  Face's dataset server and it did not answer. Labels and statistics still work." Not a modal.
- Respect the browser's concurrency; cap in-flight `/rows` calls at 3.

The `/filter` endpoint (`where="source_dataset"='…'`) exists and can drive the corpus filter
for frames outside the 600 index if the 10k view is added later. Not needed for v1.

## URL state

`#task=manipulation&corpus=egocentric-10k&judge=yes&rater=no&conf=ge99&f=<frame_id>&view=quality`

Every control writes the hash; loading a hash restores every control and scroll target. Missing
keys fall back to: `task=manipulation`, `corpus=egocentric-10k`, no filters, no selection. The
first thing a visitor sees is the biggest gap on the card (manipulation, Egocentric-10K, 80.8 vs
91.7). That default is the argument.

## Copy

Sentence case. Plain verbs. Say what a thing is, not what it proves.

- Page title: `vernier`. Subtitle: `Egocentric-10K-Evaluation · 30,000 frames · judge qwen3-vl`.
- Scale labels: `published 91.7` · `judge alone 90.0` · `measured 80.8, 95% CI 70.1–91.6`.
- Reason links: `3 frames where the judge said yes and the rater said no`.
- Empty grid: `No frames match. Loosen a filter, or open the link you were sent again.`
- No rater: `Not in the 93-frame human-gold set.`
- Rows API down: as written above.
- Timeline (there is none): do not build a placeholder tab. The evaluation release ships no clip
  or worker ids; say so once, in the Coverage caption: `Per-worker coverage needs worker ids;
  this release ships none (D039).`

Footer, one line, each item a link:
`Statistics PPI++, Gwet AC1, bootstrap · Judge Qwen3-VL-8B on Modal vLLM · 24 frames shipped,
the rest via the Hugging Face rows API · Method pre-registered, N logged decisions · Code N
tests, mypy strict · MEASUREMENT_CARD.json`

Every count in that line is read from `stats.json` at render time, never typed.

## Accessibility and quality floor

- All controls reachable and operable by keyboard; visible 2px focus ring.
- Canvas grid exposes an offscreen list of the visible tiles' frame ids as `role="listbox"`
  with `aria-activedescendant`; the detail panel is `aria-live="polite"`.
- Text contrast ≥ 4.5:1 on `--ground` and `--panel` (`--steel` on `--ground` is 4.77:1,
  `--ink` 13.5:1; `--signal` is 2.76:1 and `--human` 4.42:1, so neither ever carries text —
  labels next to a signal jaw are `--ink`). Check after any token change.
- Signal/human are also distinguished by glyph shape, not color alone.
- Works at 360px wide: scale wraps its labels, grid goes 2 across, detail stacks.
- `prefers-reduced-motion` respected.
- Lighthouse performance ≥ 90 on a throttled mobile profile with the rows API mocked.

## CLI twin — `vernier slice`

Small, in `src/vernier/cli.py`, wired as `python -m vernier slice`. Same filters as the Space
as flags; prints a table of frame ids with judge/rater/confidence; `--open` prints the Space
URL with the matching hash (and opens it with `webbrowser` if a TTY). Reads the same
`space/public/data/*.json`, so the two can never disagree. Ten tests: filter parity with the
web `SliceState` on fixed inputs, and URL round-trip.

## Out of scope for v1 (say so in the Space README, one line each)

- Pose and video timeline: no pose annotations and no clip ids in the evaluation release.
- "Measure your batch" (upload frames → judge live): needs the Modal endpoint warm and CORS on
  it; phase 2, gated on Build AI engaging.
- The 10,000-frame E2 slice: per-frame E2 responses are not committed (aggregates only).

## Acceptance

1. `make space-data && make space` from a fresh clone produces `space/dist/` with no network
   except Google Fonts at runtime.
2. Every number visible in the Space matches `MEASUREMENT_CARD.json` (test in the export).
3. Open `#task=manipulation&corpus=egocentric-10k&judge=yes&rater=no` → grid shows exactly the
   3 frames the H5 claim counts; detail panel shows all three rows for each.
4. Frames render from the rows API; kill the network → outlines + one-line notice, stats intact.
5. Keyboard-only walkthrough: pick task, filter, select a tile, read detail, copy link.
6. 10,000-tile index scrolls at 60fps in Chrome on an M-series laptop with images disabled;
   with images, no main-thread decode.
7. `python -m vernier slice --corpus epic-kitchens-100 --judge yes --rater no --open` prints
   the same frame ids the web view shows and a URL that opens to them.
