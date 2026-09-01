"""Shared concurrency helper for scripts that call a judge over many frames.

Real motivation: `scripts/e2_replication.py`/`scripts/e5_prompt_sweep.py`'s sequential
per-frame loops are fine for a smoke test (n=5-100) but would take hours for a real
distillation-scale run (~9,800 frames). `Qwen3VLJudge._call_qwen3vl` is a synchronous
`openai` HTTP call -- I/O-bound, so a thread pool gets real concurrency despite the GIL (each
thread blocks on network I/O, not CPU). The deployed server's own `target_concurrency=4`
(`cloud/modal_qwen3vl.py`) is designed for exactly this: concurrent requests within one warm
container, with Modal scaling out more containers under sustained load.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypeVar, cast

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.models import FrameRef, JudgeResponse

T = TypeVar("T")


def run_concurrent(
    items: list[T],
    fn: Callable[[T], JudgeResponse],
    *,
    max_workers: int = 8,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[JudgeResponse]:
    """Run `fn(item)` concurrently across `items` via a thread pool.

    Returns responses in the SAME ORDER as `items`, not completion order, so callers can zip
    `items` with their responses unambiguously regardless of which finished first.
    `on_progress(n_done, n_total)` is called after each completion, in completion order (not
    necessarily matching the returned list's order) -- for a long real run, this is the only
    signal anything is happening.
    """
    results: list[JudgeResponse | None] = [None] * len(items)
    n_done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_index = {pool.submit(fn, item): i for i, item in enumerate(items)}
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            results[i] = future.result()
            n_done += 1
            if on_progress is not None:
                on_progress(n_done, len(items))
    # Every future in future_to_index is awaited above (as_completed exhausts the mapping) and
    # future.result() re-raises rather than returning None on failure, so every slot is really
    # filled by this point -- the cast documents that invariant, it doesn't paper over a gap.
    return cast(list[JudgeResponse], results)


def judge_frames_concurrent(
    frames: list[FrameRef],
    variant: PromptVariant,
    judge: JudgeAdapter,
    *,
    max_workers: int = 8,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[JudgeResponse]:
    """`run_concurrent` specialized to the common case: one judge, one prompt variant, many
    frames.

    `Qwen3VLJudge._client` lazily constructs its `openai.OpenAI()` instance on first access; if
    the first several worker threads race on that access simultaneously, more than one gets
    built before `self._client_instance` is set. Harmless (a duplicate client is wasted, not
    incorrect -- both instances point at the same real `base_url`), so this is not specially
    guarded against; noted here rather than silently assumed away.
    """
    return run_concurrent(
        frames,
        lambda frame: judge.judge_frame(frame, variant),
        max_workers=max_workers,
        on_progress=on_progress,
    )
