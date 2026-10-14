"""#1134: a reasoned per-pair exception for a class a Theme holds at `error`.

Every Scene is built by hand (the two target-B pairs of #1126), so no corpus input can change what these prove.
"""
from __future__ import annotations

import json

from chrona.presentation.scene.contrast_policy import (
    ACCEPTED_CODE, EXCEPTION_UNUSED_CODE, POLICY_MEMBERS, evaluate_scene_contrast)
from tests.unit.chrona.presentation.scene.test_contrast_opt_in import _primitive, _scene, _target_b_pairs

STRICT = {member: "error" for member in POLICY_MEMBERS}
LABEL = {"purpose": "as-of-label", "over": "as-of-label-chip", "reason": "Owner-approved white on amber"}
GATE = {"role": "actual", "over": "planned", "minimum": 1.0, "reason": "An actual gate on its date coincides"}


def _by_id(exceptions, policy=STRICT):
    chip, label, planned, actual = _target_b_pairs()
    findings = evaluate_scene_contrast(_scene(chip, label, planned, actual), policy=policy, exceptions=exceptions)
    return {item.primitive_id: item for item in findings}, findings


def test_a_text_pair_at_3_72_is_a_warning_with_a_minimum_of_3_5():
    by_id, _ = _by_id([{**LABEL, "minimum": 3.5}])

    finding = by_id["as-of-label"]
    assert (finding.severity, finding.code) == ("warning", ACCEPTED_CODE)
    assert finding.accepted_code == "E_SCENE_STATE_TEXT_CONTRAST"
    assert (finding.exception_minimum, finding.exception_reason) == (3.5, "Owner-approved white on amber")
    assert round(finding.contrast_ratio, 3) == 3.717 and finding.floor == 4.5


def test_the_same_pair_is_still_an_error_with_a_minimum_of_4_0():
    by_id, _ = _by_id([{**LABEL, "minimum": 4.0}])

    assert (by_id["as-of-label"].severity, by_id["as-of-label"].code) == ("error", "E_SCENE_STATE_TEXT_CONTRAST")


def test_a_mark_pair_at_1_0_is_a_warning_with_a_minimum_of_1_0():
    by_id, _ = _by_id([GATE])

    assert (by_id["actual:gate"].severity, by_id["actual:gate"].code) == ("warning", ACCEPTED_CODE)
    assert by_id["actual:gate"].accepted_code == "E_SCENE_MARK_CONTRAST"


def test_an_entry_that_matches_no_pair_is_reported_and_one_that_did_is_not():
    _, findings = _by_id([{**LABEL, "minimum": 3.5}, {**GATE, "role": "no-such-role"},
                          {**GATE, "over": "no-such-ground"}])

    unused = [item for item in findings if item.code == EXCEPTION_UNUSED_CODE]
    assert [(item.severity, item.disposition) for item in unused] == [
        ("warning", "exceptions[1]"), ("warning", "exceptions[2]")]


def test_a_pair_below_the_minimum_still_counts_the_entry_as_used():
    _, findings = _by_id([{**LABEL, "minimum": 4.0}])

    assert not [item for item in findings if item.code == EXCEPTION_UNUSED_CODE]


def test_over_any_and_the_first_matching_entry_in_declaration_order_decide():
    by_id, _ = _by_id([{**LABEL, "over": "any", "minimum": 4.0}, {**LABEL, "minimum": 3.5}])

    assert by_id["as-of-label"].severity == "error"  # the first entry matched, and 4.0 is not met


def test_a_class_below_error_has_nothing_to_accept_so_its_entry_is_unused():
    by_id, findings = _by_id([{**LABEL, "minimum": 3.5}], policy={**STRICT, "groundText": "warning", "stateText": "warning"})

    assert by_id["as-of-label"].code == "W_SCENE_STATE_TEXT_CONTRAST"
    assert [item.code for item in findings if item.code == EXCEPTION_UNUSED_CODE] == [EXCEPTION_UNUSED_CODE]


def test_absent_entries_are_byte_identical():
    chip, label, planned, actual = _target_b_pairs()
    scene = _scene(chip, label, planned, actual)

    def dump(**kwargs):
        return json.dumps([item.as_mapping() for item in evaluate_scene_contrast(scene, policy=STRICT, **kwargs)])

    assert dump() == dump(exceptions=()) == dump(exceptions=[])
    assert "acceptedCode" not in dump() and EXCEPTION_UNUSED_CODE not in dump()


def test_a_structural_error_is_never_accepted():
    broken = _primitive("x", "planned", "planned", "#FFFFFF")
    broken["paint"]["opacity"] = 7
    findings = evaluate_scene_contrast(_scene(broken), policy=STRICT,
                                       exceptions=[{"role": "planned", "over": "any", "minimum": 0.1, "reason": "r"}])

    assert [item.code for item in findings if item.primitive_id == "x"] == ["E_SCENE_CONTRAST_PAINT"]
