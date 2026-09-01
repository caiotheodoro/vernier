"""Judge adapters. `ClaudeJudge`/`GeminiJudge` are retired (`docs/DECISIONS.md` D042) --
`gemini-2.5-flash` is deprecated for new API keys and Anthropic is out of the panel entirely.
`Qwen3VLJudge` (self-hosted, Modal/AWS) is the sole judge."""

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant, load_prompt
from vernier.judges.qwen3vl import Qwen3VLJudge

__all__ = [
    "JudgeAdapter",
    "PromptVariant",
    "Qwen3VLJudge",
    "load_prompt",
]
