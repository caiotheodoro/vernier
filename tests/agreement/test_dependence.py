"""Tests for `judge_error_dependence` (Wave 1, unit 11).

`docs/RED-TEAM.md` A3: three judges are not three independent opinions if their errors
correlate. `docs/PRE-REGISTRATION.md` names the concept ("an explicit judge-error-dependence
estimate") but pins no formula -- these tests exercise the mean-pairwise-phi-coefficient
statistic chosen in `dependence.py`, not a pre-registered number.
"""

from __future__ import annotations

from vernier.agreement.dependence import judge_error_dependence
from vernier.models import HumanLabel, JudgeResponse, JudgeStatus

from tests.fixtures import make_human_label, make_judge_response

FRAMES = [f"frame-{i}" for i in range(1, 9)]


def _gold_all_true(frame_ids: list[str]) -> list[HumanLabel]:
    return [make_human_label(frame_id=fid, manipulation=True) for fid in frame_ids]


def _response(
    judge: str, frame_id: str, *, wrong: bool, status: JudgeStatus = "ok"
) -> JudgeResponse:
    # gold is always manipulation=True in these fixtures; "wrong" means the judge said False.
    if status != "ok":
        return make_judge_response(frame_id=frame_id, judge=judge, status=status)
    return make_judge_response(frame_id=frame_id, judge=judge, manipulation=not wrong)


def test_perfectly_correlated_errors_read_as_maximally_dependent() -> None:
    frames = FRAMES[:6]
    gold = _gold_all_true(frames)
    wrong_frames = {frames[0], frames[1], frames[2]}
    responses_by_judge = {
        "judge-a": [_response("judge-a", f, wrong=f in wrong_frames) for f in frames],
        "judge-b": [_response("judge-b", f, wrong=f in wrong_frames) for f in frames],
    }

    result = judge_error_dependence(responses_by_judge, gold)

    assert result == 1.0


def test_independent_errors_read_near_zero() -> None:
    frames = FRAMES[:4]
    gold = _gold_all_true(frames)
    # A wrong on f1,f2; B wrong on f1,f3 -- balanced 2x2 table (n11=n10=n01=n00=1) => phi=0.
    a_wrong = {frames[0], frames[1]}
    b_wrong = {frames[0], frames[2]}
    responses_by_judge = {
        "judge-a": [_response("judge-a", f, wrong=f in a_wrong) for f in frames],
        "judge-b": [_response("judge-b", f, wrong=f in b_wrong) for f in frames],
    }

    result = judge_error_dependence(responses_by_judge, gold)

    assert result == 0.0


def test_three_judges_mixed_correlation_reflects_the_mixture() -> None:
    frames = FRAMES[:8]
    gold = _gold_all_true(frames)
    # A and B: perfectly correlated (wrong on f1-f4). C: balanced/independent vs. both
    # (wrong on f1,f2,f5,f6 -- overlaps A on exactly half of each judge's wrong+right split).
    ab_wrong = {frames[0], frames[1], frames[2], frames[3]}
    c_wrong = {frames[0], frames[1], frames[4], frames[5]}
    responses_by_judge = {
        "judge-a": [_response("judge-a", f, wrong=f in ab_wrong) for f in frames],
        "judge-b": [_response("judge-b", f, wrong=f in ab_wrong) for f in frames],
        "judge-c": [_response("judge-c", f, wrong=f in c_wrong) for f in frames],
    }

    result = judge_error_dependence(responses_by_judge, gold)

    # mean of phi(a,b)=1, phi(a,c)=0, phi(b,c)=0
    assert result == 1.0 / 3.0


def test_non_ok_responses_excluded_from_error_indicator() -> None:
    frames = FRAMES[:4]
    gold = _gold_all_true(frames)
    a_wrong = {frames[0], frames[1]}
    b_wrong = {frames[0], frames[2]}
    responses_by_judge = {
        "judge-a": [_response("judge-a", f, wrong=f in a_wrong) for f in frames],
        "judge-b": [_response("judge-b", f, wrong=f in b_wrong) for f in frames],
    }
    baseline = judge_error_dependence(responses_by_judge, gold)

    # Add a non-"ok" response on a fifth frame for judge-a, matched by a gold label that
    # would (if wrongly counted as an error) skew the pairwise table. It must be excluded
    # entirely, not treated as "wrong" or "right".
    extra_frame = "frame-5"
    gold_with_extra = gold + _gold_all_true([extra_frame])
    responses_with_extra = {
        "judge-a": responses_by_judge["judge-a"]
        + [_response("judge-a", extra_frame, wrong=False, status="refused")],
        "judge-b": responses_by_judge["judge-b"],
    }

    result = judge_error_dependence(responses_with_extra, gold_with_extra)

    assert result == baseline
