"""Every render warning says what is wrong, and a repeat of one cause is one row with a count (#782)."""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.surface_quality import FitWarning
from chrona.usecases.diagnostic_messages import (
    MAX_OCCURRENCES, collapse_warnings, derived_message, describe_warning, warning_message,
)
from chrona.usecases.draft_render import warning_payloads
from chrona.usecases.warning_ledger import collect_render_warnings

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "src" / "chrona"

# The render-warning producers: Layout and Scene (identity strings, fit and perceptibility warnings), the model
# (colour separability), the attachment rule and the ledger itself. The scheduler's own diagnostics reach an
# agent through another record and are not in this scan.
PRODUCERS = (*sorted((SRC / "presentation").rglob("*.py")), SRC / "core" / "attachments.py",
             SRC / "usecases" / "warning_ledger.py")
CODE = re.compile(r"(?<![A-Za-z0-9_])(W_[A-Z0-9]+(?:_[A-Z0-9]+)*)(?![A-Za-z0-9_])")


def _emitted_codes() -> set[str]:
    found: set[str] = set()
    for path in PRODUCERS:
        found |= set(CODE.findall(path.read_text(encoding="utf-8")))
    # Perceptibility findings are `E_SCENE_*` in the evaluator and `W_SCENE_*` once projected to a warning.
    text = (SRC / "presentation" / "scene" / "perceptibility.py").read_text(encoding="utf-8")
    found |= {"W_" + code.removeprefix("E_") for code in re.findall(r'_finding\("(E_SCENE_[A-Z_]+)"', text)}
    return found


def _sample(code: str) -> dict:
    return {"code": code, "severity": "warning", "diagnostic": f"{code}:subject:one", "placementId": "p", "failureKind": "k",
            "behaviour": "b", "primitiveIds": ["a", "b"], "values": ["x", "y"], "host": "h", "sourceRef": "s"}


def test_the_scan_finds_the_warning_codes_this_test_is_about():
    codes = _emitted_codes()
    assert len(codes) >= 25
    assert {"W_LAYOUT_LABEL_SUPPRESSED", "W_FONT_GLYPH_SUBSTITUTED", "W_SCENE_TEXT_INTERSECTION",
            "W_PRESENTATION_SCALE_NOT_SEPARABLE", "W_PROJECT_ATTACHED_OUTSIDE_HOST"} <= codes


def test_every_warning_code_a_render_can_emit_has_a_curated_sentence():
    missing = sorted(code for code in _emitted_codes()
                     if describe_warning(_sample(code)).cause == derived_message(code))
    assert not missing, (
        f"{missing} have no sentence in usecases/diagnostic_messages.py: add one to describe_warning, or have the "
        "family put its own `message` in the ledger record")


def test_invalid_fan_in_warning_explains_the_group_failure_and_names_its_relations():
    text = describe_warning({"code": "W_SCENE_RELATION_FAN_IN_INVALID",
                             "primitiveIds": ["relation:one", "relation:two"]})
    assert text.cause == "shared dependency arrivals do not agree on their target port, terminal owner, paint, or approach direction"
    assert text.subject == "relation:one, relation:two"


def test_a_family_that_carries_its_own_message_keeps_it_and_only_equal_messages_merge():
    one = {"code": "W_NEW_FAMILY", "severity": "warning", "diagnostic": "W_NEW_FAMILY:a", "message": "a is late by 2 days"}
    other = dict(one, diagnostic="W_NEW_FAMILY:b", message="b is late by 5 days")
    rows = collapse_warnings([one, other, dict(one, diagnostic="W_NEW_FAMILY:a2")])
    assert [(row["message"], row.get("count")) for row in rows] == [
        ("a is late by 2 days (2 times)", 2), ("b is late by 5 days", None)]


def test_an_unknown_code_without_a_message_gets_the_derived_sentence_and_its_subject():
    row = collapse_warnings([{"code": "W_BRAND_NEW", "severity": "warning", "diagnostic": "W_BRAND_NEW:thing"}])[0]
    assert row["message"] == f"{derived_message('W_BRAND_NEW')}: thing"
    assert collapse_warnings([row])[0]["message"] == row["message"]  # idempotent


def _label(index: int, code: str = "W_LAYOUT_LABEL_SUPPRESSED") -> dict:
    return {"code": code, "severity": "warning", "diagnostic": f"{code}:member-label:o{index}:o{index}"}


def test_seven_repeats_of_one_cause_are_one_row_with_a_count_the_first_identity_and_the_rest_listed():
    rows = collapse_warnings([_label(index) for index in range(7)])
    (row,) = rows
    assert row["count"] == 7 and row["diagnostic"] == "W_LAYOUT_LABEL_SUPPRESSED:member-label:o0:o0"
    assert row["occurrences"] == [f"W_LAYOUT_LABEL_SUPPRESSED:member-label:o{index}:o{index}" for index in range(7)]
    assert row["message"] == ("a label was left out of the picture because it does not fit: "
                              "member-label:o0:o0 and 6 more")
    assert (row["code"], row["severity"]) == ("W_LAYOUT_LABEL_SUPPRESSED", "warning")


def test_one_warning_is_not_merged_and_has_no_count_or_occurrences():
    (row,) = collapse_warnings([_label(1)])
    assert "count" not in row and "occurrences" not in row
    assert row["message"] == "a label was left out of the picture because it does not fit: member-label:o1:o1"


def test_different_causes_stay_apart_even_under_one_code_family_and_order_follows_first_occurrence():
    def fit(code, kind, placement):
        return {"code": code, "severity": "warning", "diagnostic": f"{code}:{placement}", "placementId": placement,
                "sourceRef": f"/objects/{placement}", "failureKind": kind, "behaviour": "visible-overflow", "requiredInline": 10, "requiredBlock": 5,
                "availableInline": 4, "availableBlock": 5}

    rows = collapse_warnings([
        fit("W_LAYOUT_VISIBLE_OVERFLOW", "label-collision", "a"), _label(1),
        fit("W_LAYOUT_VISIBLE_OVERFLOW", "title-width", "b"), fit("W_LAYOUT_VISIBLE_OVERFLOW", "label-collision", "c"),
        _label(2, "W_LAYOUT_RELATION_LABEL_SUPPRESSED")])
    assert [(row["code"], row.get("count")) for row in rows] == [
        ("W_LAYOUT_VISIBLE_OVERFLOW", 2), ("W_LAYOUT_LABEL_SUPPRESSED", None),
        ("W_LAYOUT_VISIBLE_OVERFLOW", None), ("W_LAYOUT_RELATION_LABEL_SUPPRESSED", None)]
    assert rows[0]["message"].endswith("a (needs 10x5, has 4x5) and 1 more")
    assert rows[0]["sourceRef"] == "/objects/a"  # the first occurrence's sourceRef, not the last
    assert "(label-collision, visible-overflow)" in rows[0]["message"]


def test_severity_is_part_of_the_cause_and_counts_stay_exact_beyond_the_listing_cap():
    warnings = [_label(index) for index in range(MAX_OCCURRENCES + 10)]
    infos = [dict(_label(0), severity="info")]
    rows = collapse_warnings([*warnings, *infos])
    assert [(row["severity"], row.get("count")) for row in rows] == [("warning", MAX_OCCURRENCES + 10), ("info", None)]
    assert len(rows[0]["occurrences"]) == MAX_OCCURRENCES


def test_an_identity_that_repeats_is_counted_every_time_and_listed_once():
    rows = collapse_warnings([_label(1), _label(1), _label(2)])
    assert rows[0]["count"] == 3 and rows[0]["occurrences"] == [
        "W_LAYOUT_LABEL_SUPPRESSED:member-label:o1:o1", "W_LAYOUT_LABEL_SUPPRESSED:member-label:o2:o2"]


def test_the_message_shape():
    assert warning_message(describe_warning(_label(1))).endswith(": member-label:o1:o1")
    bare = describe_warning({"code": "W_LAYOUT_ACTUAL_INCOMPLETE", "diagnostic": "W_LAYOUT_ACTUAL_INCOMPLETE"})
    assert bare.subject == "" and warning_message(bare, 3).endswith("not drawn (3 times)")


def test_a_ledger_record_carries_a_message_and_equal_causes_collapse_through_the_use_case_payloads():
    records = collect_render_warnings(
        surface_diagnostics=[f"W_LAYOUT_LABEL_SUPPRESSED:member-label:o{index}:o{index}" for index in range(3)],
        tabular_warnings=(), glyph_warnings=(), perceptibility_warnings=(), scale_collisions=(),
        attachment_warnings=(SimpleNamespace(code="W_PROJECT_ATTACHED_OUTSIDE_HOST", object_id="o", host_id="h"),),
        fit_warnings=(FitWarning("W_LAYOUT_ROW_DENSITY", "row:a", "a", "review-row-density", "visible-overflow", 1, 2, 3, 4),))
    assert all(record.payload["message"].strip() for record in records)
    payloads = warning_payloads(SimpleNamespace(warning_records=records, info_diagnostics=()))
    assert [(item["code"], item.get("count")) for item in payloads] == [
        ("W_LAYOUT_LABEL_SUPPRESSED", 3), ("W_LAYOUT_ROW_DENSITY", None), ("W_PROJECT_ATTACHED_OUTSIDE_HOST", None)]
    assert payloads[2]["message"] == "an attached object is dated outside the planned span of its host h: o"


def test_an_ellipsized_text_warning_says_what_was_shortened_and_by_how_much():
    # #497: the legend's shortened labels carry a typed fit warning with a plain-language cause.
    text = describe_warning({
        "code": "W_LAYOUT_TEXT_ELLIPSIZED", "diagnostic": "W_LAYOUT_TEXT_ELLIPSIZED:legend:a", "placementId": "legend:a",
        "failureKind": "legend-text", "behaviour": "ellipsize-with-source", "requiredInline": 120.5,
        "requiredBlock": 20, "availableInline": 40, "availableBlock": 30})

    assert text.cause == "text was shortened with an ellipsis to fit its box (legend-text, ellipsize-with-source)"
    assert text.subject == "legend:a (needs 120.5x20, has 40x30)"
