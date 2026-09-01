"""Prompt registry. `P0a`/`P0b` are pinned verbatim in `docs/upstream/`; `P1`-`P7` are fixed
in `docs/PRE-REGISTRATION.md`. No variant is added after that file is frozen.
"""

from __future__ import annotations

from vernier.models import PromptVariant

__all__ = ["PromptVariant", "load_prompt"]


def load_prompt(variant: PromptVariant, *, task: str) -> str:
    """Return the pinned prompt text for `variant` and `task` ("hand_count" or "manipulation").

    `P0a`/`P0b` load verbatim from `docs/upstream/`; `P1`-`P7` are derived from `P0b` per the
    single change each makes, as tabulated in `docs/PRE-REGISTRATION.md`.
    """
    raise NotImplementedError
