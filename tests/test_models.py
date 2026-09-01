import pytest
from pydantic import ValidationError

from tests.fixtures import ALL_MALFORMED, ALL_VALID
from vernier.models import (
    AgreementCI,
    AgreementResult,
    CalibrationReport,
    Confidence,
    FrameRef,
    HumanLabel,
    JudgeResponse,
    MeasurementCard,
    PPIBlock,
    PrevalenceEstimate,
    ProbeResult,
    Record,
)

MALFORMED_MODEL: dict[str, type[Record]] = {
    "FrameRef": FrameRef,
    "JudgeResponse": JudgeResponse,
    "HumanLabel": HumanLabel,
    "PPIBlock": PPIBlock,
    "Confidence": Confidence,
    "AgreementCI": AgreementCI,
}


@pytest.mark.parametrize("name", list(ALL_VALID))
def test_fixture_is_valid_record(name: str) -> None:
    instance = ALL_VALID[name]
    assert isinstance(instance, Record)
    # Round-trips through JSON without loss, using each field's canonical CONTRACTS.md key
    # (its alias, where one is declared -- e.g. HumanLabel.pass_ serializes as "pass").
    reloaded = type(instance).model_validate_json(instance.model_dump_json(by_alias=True))
    assert reloaded == instance


@pytest.mark.parametrize("name,payload", list(ALL_MALFORMED.items()))
def test_fixture_is_rejected(name: str, payload: dict[str, object]) -> None:
    model_name = name.split(".", 1)[0]
    model = MALFORMED_MODEL[model_name]
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def test_all_nine_record_types_covered() -> None:
    covered = {type(v).__name__ for v in ALL_VALID.values()}
    expected = {
        "FrameRef",
        "JudgeResponse",
        "HumanLabel",
        "AgreementResult",
        "PrevalenceEstimate",
        "CalibrationReport",
        "ProbeResult",
        "MeasurementCard",
    }
    assert expected <= covered


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        FrameRef.model_validate(
            {
                **ALL_VALID["FrameRef"].model_dump(),
                "not_a_contract_field": True,
            }
        )


@pytest.mark.parametrize(
    "model",
    [FrameRef, JudgeResponse, HumanLabel, AgreementResult, PrevalenceEstimate, CalibrationReport, ProbeResult, MeasurementCard],
)
def test_records_are_frozen(model: type[Record]) -> None:
    key = next(k for k in ALL_VALID if k.split(".")[0] == model.__name__)
    instance = ALL_VALID[key]
    field_name = next(iter(model.model_fields))
    with pytest.raises(ValidationError):
        setattr(instance, field_name, getattr(instance, field_name))
