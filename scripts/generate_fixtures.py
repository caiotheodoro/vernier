"""Write every fixture in `tests/fixtures.py` to disk as JSON.

Wave 1's 18-way fan-out builds against these offline, without importing `tests/`. Regenerate
with `make fixtures` whenever `CONTRACTS.md` or `tests/fixtures.py` changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from tests.fixtures import ALL_MALFORMED, ALL_VALID  # noqa: E402


def _safe_name(name: str) -> str:
    return name.replace(".", "__")


def main() -> None:
    valid_dir = REPO_ROOT / "tests" / "fixtures" / "valid"
    malformed_dir = REPO_ROOT / "tests" / "fixtures" / "malformed"
    valid_dir.mkdir(parents=True, exist_ok=True)
    malformed_dir.mkdir(parents=True, exist_ok=True)

    for name, instance in ALL_VALID.items():
        out = valid_dir / f"{_safe_name(name)}.json"
        out.write_text(instance.model_dump_json(indent=2, by_alias=True) + "\n")
        print(f"wrote {out.relative_to(REPO_ROOT)}")

    for name, payload in ALL_MALFORMED.items():
        out = malformed_dir / f"{_safe_name(name)}.json"
        out.write_text(json.dumps(payload, indent=2, default=str) + "\n")
        print(f"wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
