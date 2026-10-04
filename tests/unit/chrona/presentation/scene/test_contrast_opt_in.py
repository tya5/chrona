"""#1126: contrast constraints are an opt-in design option.

A Theme sets each class of finding `none`, `warning` or `error`; the evaluator turns a floor miss into the
matching finding. Every Scene here is built by hand, so no corpus input can change what these tests prove.
"""
from __future__ import annotations

import pytest

from chrona.presentation.scene.contrast_policy import (
    BLOCKING_CODES, DEFAULT_POLICY, POLICY_MEMBERS, WARNING_BLOCKING_CODES, evaluate_scene_contrast, policy_member_of)

WHITE = "#FFFFFF"
FAINT = "#F4F4F4"
BOX = {"inline": 10, "block": 10, "inlineSize": 20, "blockSize": 10}


def _scene(*primitives):
    return {"version": "chrona/scene/v0.6", "kind": "scene", "surfaces": [{
        "id": "review", "canvasPaint": {"fill": WHITE, "opacity": 1}, "primitives": list(primitives),
        "decorationDispositions": [],
    }]}


def _primitive(identifier, role, purpose, fill, *, kind="Rect", order=100, opacity=1, treatment=None):
    value = {"id": identifier, "visualRole": role, "purpose": purpose, "kind": kind, "paintOrder": order,
             "bounds": BOX, "paint": {"fill": fill, "opacity": opacity}}
    if treatment is not None:
        value["contrastTreatment"] = treatment
    return value


# member -> (the Scene that misses its floor for that class, the finding's primitive id, code at error, code at warning)
CASES = {
    "mark": ((_primitive("x", "planned", "planned", WHITE),), "x",
             "E_SCENE_MARK_CONTRAST", "W_SCENE_MARK_CONTRAST"),
    "stateText": ((_primitive("x", "variance-ahead", "table-cell", WHITE, treatment="required"),), "x",
                  "E_SCENE_STATE_TEXT_CONTRAST", "W_SCENE_STATE_TEXT_CONTRAST"),
    "groundText": ((_primitive("x", "text", "group-header", WHITE, kind="Text"),), "x",
                   "E_SCENE_STATE_TEXT_CONTRAST", "W_SCENE_STATE_TEXT_CONTRAST"),
    "decoration": ((_primitive("x", "row-band", "row-decoration", FAINT, order=10),), "x",
                   "E_SCENE_DECORATION_CONTRAST", "W_SCENE_DECORATION_CONTRAST"),
    "unsupportedGround": ((_primitive("host", "row-band", "row-decoration", "#000000", order=10, opacity=2),  # not in [0, 1]
                           _primitive("x", "planned", "planned", "#000000")), "x",
                          "E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "W_SCENE_CONTRAST_GROUND_UNSUPPORTED"),
}


def _finding(member, severity):
    primitives, identifier, *_ = CASES[member]
    findings = evaluate_scene_contrast(_scene(*primitives), policy={member: severity})
    return next(item for item in findings if item.primitive_id == identifier)


@pytest.mark.parametrize("member", POLICY_MEMBERS)
def test_error_is_the_blocking_finding_with_its_code(member):
    finding = _finding(member, "error")

    assert (finding.severity, finding.code) == ("error", CASES[member][2])


@pytest.mark.parametrize("member", POLICY_MEMBERS)
def test_warning_is_the_same_finding_with_its_warning_code(member):
    finding = _finding(member, "warning")

    assert (finding.severity, finding.code) == ("warning", CASES[member][3])
    assert WARNING_BLOCKING_CODES[finding.code] == CASES[member][2]
    assert policy_member_of(finding) == member


@pytest.mark.parametrize("member", POLICY_MEMBERS)
def test_none_keeps_the_measured_row_and_reports_nothing(member):
    finding = _finding(member, "none")

    assert finding.severity == "info" and finding.code == CASES[member][2]
    if member != "unsupportedGround":
        assert finding.contrast_ratio is not None and finding.contrast_ratio < finding.floor


@pytest.mark.parametrize("member", POLICY_MEMBERS)
def test_a_class_is_governed_by_its_own_member_only(member):
    others = {other: "none" for other in POLICY_MEMBERS if other != member}
    primitives, identifier, error_code, _ = CASES[member]
    findings = evaluate_scene_contrast(_scene(*primitives), policy={**others, member: "error"})

    assert (next(item for item in findings if item.primitive_id == identifier).severity) == "error"
    relaxed = evaluate_scene_contrast(_scene(*primitives), policy={**{other: "error" for other in others}, member: "none"})
    assert next(item for item in relaxed if item.primitive_id == identifier).severity == "info"


def _target_b_pairs():
    """The two owner-approved pairs that motivated #1126, as hand-built Scenes (no corpus input)."""
    chip = _primitive("as-of-label-chip", "as-of-label-chip", "label-chip", "#B8761F", order=50)
    away = {"inline": 100, "block": 10, "inlineSize": 20, "blockSize": 10}
    chip["bounds"] = away
    label = _primitive("as-of-label", "text", "as-of-label", WHITE, kind="Text", order=300)  # white on amber: 3.717
    label["bounds"] = away
    planned = _primitive("planned:gate", "planned", "planned", "#101828", order=100)
    actual = _primitive("actual:gate", "actual", "actual", "#101828", order=110)  # the same ink on the planned gate
    return chip, label, planned, actual


def test_the_two_target_b_pairs_are_warnings_under_the_theme_default_and_errors_under_the_strict_gate():
    chip, label, planned, actual = _target_b_pairs()
    by_id = {item.primitive_id: item for item in evaluate_scene_contrast(
        _scene(chip, label, planned, actual), policy=DEFAULT_POLICY)}

    assert round(by_id["as-of-label"].contrast_ratio, 3) == 3.717 and by_id["as-of-label"].floor == 4.5
    assert (by_id["as-of-label"].severity, by_id["as-of-label"].code) == ("warning", "W_SCENE_STATE_TEXT_CONTRAST")
    assert round(by_id["actual:gate"].contrast_ratio, 3) == 1.0 and by_id["actual:gate"].floor == 3.0
    assert (by_id["actual:gate"].severity, by_id["actual:gate"].code) == ("warning", "W_SCENE_MARK_CONTRAST")
    strict = {item.primitive_id: item for item in evaluate_scene_contrast(_scene(chip, label, planned, actual))}
    assert (strict["as-of-label"].severity, strict["actual:gate"].severity) == ("error", "error")


def test_the_theme_default_never_blocks_any_class():
    assert set(DEFAULT_POLICY) == set(POLICY_MEMBERS) and set(DEFAULT_POLICY.values()) == {"warning"}
    for member in POLICY_MEMBERS:
        primitives, *_ = CASES[member]
        findings = evaluate_scene_contrast(_scene(*primitives), policy=DEFAULT_POLICY)
        assert not [item for item in findings if item.severity == "error" and item.code in BLOCKING_CODES], member
        assert [item for item in findings if item.severity == "warning"], member


def test_without_a_policy_the_evaluator_keeps_todays_gate():
    for member in ("mark", "stateText", "groundText", "unsupportedGround"):
        primitives, identifier, error_code, _ = CASES[member]
        finding = next(item for item in evaluate_scene_contrast(_scene(*primitives)) if item.primitive_id == identifier)
        assert (finding.severity, finding.code) == ("error", error_code)
    primitives, identifier, _, warning_code = CASES["decoration"]
    finding = next(item for item in evaluate_scene_contrast(_scene(*primitives)) if item.primitive_id == identifier)
    assert (finding.severity, finding.code) == ("warning", warning_code)


@pytest.mark.parametrize("severity", ["none", "warning", "error"])
def test_a_structural_finding_is_never_softened_by_the_policy(severity):
    mark = _primitive("x", "planned", "planned", WHITE)
    mark["paint"]["opacity"] = 7
    missing = _primitive("y", "variance-on-track", "table-cell", WHITE)  # no contrast treatment
    unpainted = _primitive("z", "planned", "planned", "transparent")  # no readable colour channel at all
    findings = evaluate_scene_contrast(_scene(mark, missing, unpainted),
                                       policy={member: severity for member in POLICY_MEMBERS})
    by_id = {item.primitive_id: item for item in findings}

    assert (by_id["z"].code, by_id["z"].severity) == ("E_SCENE_CONTRAST_PAINT", "error")
    assert (by_id["x"].code, by_id["x"].severity) == ("E_SCENE_CONTRAST_PAINT", "error")
    assert (by_id["y"].code, by_id["y"].severity) == ("E_SCENE_STATE_TEXT_CONTRAST_TREATMENT", "error")


def test_a_legible_pair_is_info_under_every_policy():
    mark = _primitive("x", "planned", "planned", "#000000")
    for severity in ("none", "warning", "error"):
        findings = evaluate_scene_contrast(_scene(mark), policy={member: severity for member in POLICY_MEMBERS})
        assert {item.severity for item in findings} == {"info"}


@pytest.mark.parametrize("policy", [{"marks": "error"}, {"mark": "off"}, {"mark": False}, {"mark": None}])
def test_an_unknown_member_or_value_is_refused(policy):
    with pytest.raises(ValueError):
        evaluate_scene_contrast(_scene(_primitive("x", "planned", "planned", WHITE)), policy=policy)


def test_every_blocking_code_is_a_floor_or_ground_code_with_a_warning_twin():
    assert BLOCKING_CODES == {"E_SCENE_MARK_CONTRAST", "E_SCENE_STATE_TEXT_CONTRAST", "E_SCENE_DECORATION_CONTRAST",
                              "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"}
