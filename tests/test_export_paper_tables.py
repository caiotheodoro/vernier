"""The paper's tables are generated, not typed (docs/DECISIONS.md D086).

The committed files under `paper/generated/` must equal a fresh build, the same rule
`tests/test_export_space_data.py` applies to the Space payload and for the same reason: a
generated artifact that has drifted from its generator is worse than no artifact.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from export_paper_tables import (  # noqa: E402
    _design_effect,
    _error_direction,
    _ledger,
    _load,
    _margins,
    _prevalence,
    _provenance,
    _replication,
    _tex_escape,
)

_GENERATED = _ROOT / "paper" / "generated"


@pytest.fixture(scope="module")
def data() -> dict[str, Any]:
    return _load()


@pytest.mark.parametrize(
    "name,builder",
    [
        ("replication", _replication),
        ("error_direction", _error_direction),
        ("prevalence", _prevalence),
        ("margins", _margins),
        ("design_effect", _design_effect),
        ("ledger", _ledger),
    ],
)
def test_committed_table_equals_a_fresh_build(
    name: str, builder: Callable[[dict[str, Any]], str], data: dict[str, Any]
) -> None:
    assert (_GENERATED / f"{name}.tex").read_text() == builder(data)


def test_provenance_digest_is_the_committed_card(data: dict[str, Any]) -> None:
    """The paper states the digest it was built against; it must be the real one."""
    committed = (_GENERATED / "provenance.tex").read_text()
    digest = data["card"]["content_digest"].replace("sha256:", "")[:16]
    assert f"{{{digest}}}" in committed
    assert f"{{{data['wave4']['n_primary']}}}" in committed


def test_underscores_are_escaped_for_tex(data: dict[str, Any]) -> None:
    """NOT_VERIFIED carries an underscore, which is a subscript operator in TeX."""
    assert _tex_escape("NOT_VERIFIED") == r"NOT\_VERIFIED"
    assert r"NOT\_VERIFIED" in (_GENERATED / "provenance.tex").read_text()


def test_every_table_is_a_complete_booktabs_tabular(data: dict[str, Any]) -> None:
    for path in sorted(_GENERATED.glob("*.tex")):
        tex = path.read_text()
        if path.name == "provenance.tex":
            assert tex.count("\\newcommand") >= 5
            continue
        assert tex.startswith("\\begin{tabular}"), path.name
        assert tex.rstrip().endswith("\\end{tabular}"), path.name
        assert tex.count("\\toprule") == tex.count("\\bottomrule") == 1, path.name


def test_the_ledger_carries_every_pre_registered_hypothesis(data: dict[str, Any]) -> None:
    ledger = _ledger(data)
    for h in ("H1", "H1b", "H2", "H3", "H4", "H5", "H6", "H7", "H8"):
        assert f"{h} &" in ledger, f"{h} missing from the hypothesis ledger"
    assert "exploratory" in ledger
