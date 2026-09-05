// Mirrors scripts/export_space_data.py's output schema. Every number on the page comes from
// stats.json; nothing numeric is typed into a component.

export type Corpus = "egocentric-10k" | "ego4d" | "epic-kitchens-100" | "egocentric-100k";
export type GoldCorpus = "egocentric-10k" | "ego4d" | "epic-kitchens-100";
export type Task = "hand_count" | "hand_eq2" | "manipulation";
export type JudgeStatus = "ok" | "unparseable" | "refused" | "timeout" | "error";
export type Hands = 0 | 1 | 2;

export const TASKS: readonly Task[] = ["hand_count", "hand_eq2", "manipulation"];

export const TASK_LABEL: Record<Task, string> = {
  hand_count: "at least one hand",
  hand_eq2: "both hands",
  manipulation: "active manipulation",
};

export const CORPUS_LABEL: Record<Corpus, string> = {
  "egocentric-10k": "Egocentric-10K",
  ego4d: "Ego4D",
  "epic-kitchens-100": "EPIC-KITCHENS-100",
  "egocentric-100k": "Egocentric-100K",
};

// docs/RUBRIC.md's closed tag list, mirroring src/vernier/models.py's EdgeCaseTag.
export type EdgeCaseTag =
  | "partial"
  | "glove"
  | "tool-occlusion"
  | "reflection"
  | "blur"
  | "edge"
  | "undecidable"
  | "between-actions"
  | "self-contact"
  | "other-person";

/** Where a frame's thumbnail sits in the committed atlas. */
export type AtlasRef = { x: number; y: number; w: number; h: number };

export type Frame = {
  id: string;
  corpus: GoldCorpus;
  w: number;
  h: number;
  row: number;
  /** The judge: answer, confidence, status, and its literal output string. */
  q: {
    h: Hands | null;
    m: boolean | null;
    c: number | null;
    s: JudgeStatus;
    raw: string;
    lat: number;
    cost: number;
  };
  /** Build AI's own stored label for this frame. */
  g: { h: Hands; m: boolean } | null;
  /** The human rater, on 93 of the 600. */
  r: {
    h: Hands;
    m: boolean;
    d: "easy" | "medium" | "hard";
    note: string | null;
    e: EdgeCaseTag[];
    s: number;
    at: string;
    /**
     * The rater's later re-read of this frame (D074). Their current answer, and what the page
     * shows. Every statistic still comes from the pre-registered fields above: the review set
     * was selected by disagreement, and a set selected that way can only move agreement one way.
     */
    rr?: {
      h: Hands;
      m: boolean;
      d: "easy" | "medium" | "hard";
      e: EdgeCaseTag[];
      s: number;
      at: string;
      changed: boolean;
    };
  } | null;
  /**
   * Non-null only where the frame ships with this page. `null` is the flag the UI reads: the
   * rule is not "which corpus" but "which corpus AND is anyone else in shot"
   * (docs/ETHICS.md §4, D073), so tier can never be inferred from `corpus`.
   */
  t: AtlasRef | null;
};

export type PpiEntry = {
  naive: number;
  n_judged: number;
  value: number;
  lo: number;
  hi: number;
  level: number;
  n_gold: number;
  n_unlabelled: number;
  method: string;
  clustered: boolean;
  why_not_clustered: string | null;
  judge: string;
  prompt_variant: string;
};

export type JudgeAlone = {
  hand_count: { rate: number; n: number };
  hand_eq2: { rate: number; n: number };
  manipulation: { rate: number; n: number };
  judge: string;
  prompt_variant: string;
  sample: string;
};

export type AgreementEntry = {
  ac1: number;
  lo: number;
  hi: number;
  ci_method: string;
  kappa: number;
  raw: number;
  n: number;
};

export type CalibrationBin = {
  lo: number;
  hi: number;
  n: number;
  mean_conf: number | null;
  accuracy: number | null;
};

export type Run = {
  id: string;
  sample: string;
  corpus: string;
  n_requested: number;
  n_ok: number | null;
  status_counts: Record<string, number> | null;
  cost_usd: number | null;
  judge_time_ms: number | null;
  latency_ms: number[] | null;
  notes: string;
};

export type H1Entry = {
  published: number;
  observed: number;
  diff_pp: number;
  within_tolerance: boolean;
};

export type H1Block = {
  tasks: Record<Task, H1Entry>;
  tolerance_pp: number;
  n: number;
  pre_registered: boolean;
};

export type Interval = { lo: number; hi: number; method: string; clusters: number | null; B: number | null };

export type H2Task = {
  point_estimate: number;
  iid: Interval;
  cluster: Interval;
  design_effect: number;
  why_absent: string | null;
};

export type H2Arm = {
  n_ok: number;
  clusters: {
    n_clusters: number;
    n_observations: number;
    mean_cluster_size: number;
    min_cluster_size: number;
    max_cluster_size: number;
  };
  tasks: Record<"hand_ge1" | "hand_eq2" | "active_manipulation", H2Task>;
};

export type H2Block = {
  arms: Record<string, H2Arm>;
  threshold: number;
  holds: boolean;
  cluster_by: string;
  seed: number;
  B: number;
  design_effect_min: number;
  design_effect_max: number;
  /** sqrt(deff) - 1: how much narrower an iid interval is. Not a rescaled interval. */
  width_understatement_pct: { lo: number; hi: number };
};

export type TestRetest = {
  n_frames: number;
  repeats_per_frame: number;
  judge_rev: string;
  judge_config: string;
  hand_count_self_agreement_rate: number;
  manipulation_self_agreement_rate: number;
  per_frame: {
    frame_id: string;
    statuses: string[];
    hand_counts: number[];
    manipulations: boolean[];
    hand_count_unanimous: boolean;
    manipulation_unanimous: boolean;
  }[];
};

export type Thumbnails = {
  n: number;
  corpus: GoldCorpus;
  tile: { w: number; h: number };
  atlas: { file: string; w: number; h: number; cols: number; rows: number; n_tiles: number; bytes: number };
  n_withheld_for_likeness: number;
  source: { dataset: string; revision: string; license: string; source_dataset: string };
};

export type Stats = {
  generated_from: {
    card_digest: string;
    git_rev: string;
    judge: string;
    judge_rev: string;
    prompt_variant: string;
    dataset: string;
    dataset_rev: string;
    n_gold_frames: number;
    n_rater_labels: number;
  };
  corpora: Corpus[];
  rows_api: {
    dataset: string;
    config: string;
    split: string;
    source_dataset: Record<GoldCorpus, string>;
    file_order: GoldCorpus[];
  };
  published: Partial<Record<Corpus, Partial<Record<Task, number>>>>;
  h1: Partial<Record<Corpus, H1Block>>;
  h2: H2Block;
  test_retest: TestRetest;
  thumbnails: Thumbnails;
  ppi: Partial<Record<Corpus, Partial<Record<Task, PpiEntry>>>>;
  judge_alone: Partial<Record<Corpus, JudgeAlone>>;
  agreement: {
    h4: Record<"hand_count" | "manipulation", AgreementEntry>;
    intra_rater: Record<
      "hand_count" | "manipulation",
      { ac1: number; lo: number; hi: number; ci_method: string; kappa: number; n_pairs: number }
    >;
    h5: {
      "egocentric-10k": { n: number; error_rate: number };
      "epic-kitchens-100": { n: number; error_rate: number };
      diff_pp: number;
      holds: boolean;
    };
  };
  confusion: { hands: number[][]; manipulation: number[][]; n: number };
  calibration: Record<
    "hand_count" | "manipulation",
    { ece: number; n: number; confidence_kind: string; bins: CalibrationBin[] }
  >;
  coverage: Partial<
    Record<Corpus, { hands: [number, number, number]; manipulation: [number, number]; n: number; source: string }>
  >;
  prompt_sweep: {
    hand_count: Record<string, number>;
    manipulation: Record<string, number>;
    n: number;
    hand_count_spread_pp: number;
    manipulation_spread_pp: number;
  };
  runs: Run[];
  health: {
    e2_frames: number;
    e2_cost_both_arms_usd: number;
    e2_judge_time_both_arms_h: number;
    e2_arms: Record<"P0a" | "P0b", { cost_usd: number; judge_time_h: number }>;
    gold_calls: { n: number; p50_ms: number; p95_ms: number; max_ms: number; latency_ms: number[] };
  };
  provenance: Record<string, { claim_ref: string; decision: string }>;
  repo: { n_tests: number; n_decisions: number };
};

export const REPO_URL = "https://github.com/caiotheodoro/vernier";
export const HF_DATASET_URL = "https://huggingface.co/datasets/caiotheodoro/vernier";
export const SOURCE_DATASET_URL = "https://huggingface.co/datasets/builddotai/Egocentric-10K-Evaluation";

export function repoFile(path: string): string {
  return `${REPO_URL}/blob/main/${path}`;
}
