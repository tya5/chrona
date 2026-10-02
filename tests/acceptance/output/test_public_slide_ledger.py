"""#977: every public slide is accounted for and none changes silently, with no literal total in a test.

The slides are the ones the manifests declare; the per-slide numbers live in `public-slide-ledger.yaml`.
The rule is a pure function, tested here on hand-built input; the corpus test feeds it the real slides.
"""
from dataclasses import replace

from tests.support.public_evidence import (
    LEDGER, Observed, compare_ledger, declared_slides, format_row, load_ledger, observe_all, relation_problems,
)

BASE = Observed(axis_labels=7, svg_axis_labels=7, dvt_hosted=False, chips=())


def _ledger(**rows):
    return {key.replace("__", "/"): row for key, row in rows.items()}


def test_every_declared_slide_is_accounted_for_and_shows_what_its_ledger_row_says():
    assert compare_ledger(observe_all(), load_ledger()) == []


def test_the_svg_draws_exactly_the_axis_labels_the_scene_carries():
    assert relation_problems(observe_all()) == []


def test_every_declared_slide_has_generated_evidence_and_the_ledger_is_sorted_one_line_per_slide():
    assert all(slide.svg.is_file() and (slide.scene is None or slide.scene.is_file()) for slide in declared_slides())
    rows = [line for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.startswith("  ")]
    keys = [line.split(":", 1)[0].strip() for line in rows]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys)) == len(load_ledger())


# --- the rule, on synthetic input -----------------------------------------------------------------

def test_matching_rows_pass_and_a_default_row_means_not_hosted_and_no_chips():
    assert compare_ledger({"a/x": BASE}, _ledger(a__x={"axisLabels": 7})) == []


def test_a_slide_with_no_row_is_not_accounted_for_and_the_message_gives_the_row_to_add():
    problems = compare_ledger({"a/x": BASE, "a/new": replace(BASE, chips=("chip:as-of-label",))}, _ledger(a__x={"axisLabels": 7}))
    assert len(problems) == 1 and problems[0].startswith("a/new: no ledger row")
    assert "a/new: {axisLabels: 7, chips: ['chip:as-of-label']}" in problems[0]


def test_a_row_without_a_slide_is_stale():
    problems = compare_ledger({"a/x": BASE}, _ledger(a__x={"axisLabels": 7}, a__gone={"axisLabels": 1}))
    assert problems == ["a/gone: ledger row without a manifest slide; remove it"]


def test_each_changed_value_is_reported_with_the_observed_and_the_recorded_value():
    seen = Observed(axis_labels=8, svg_axis_labels=8, dvt_hosted=True, chips=("chip:b",))
    problems = compare_ledger({"a/x": seen}, _ledger(a__x={"axisLabels": 7, "chips": ["chip:a"]}))
    assert [text.split(" is ")[0] for text in problems] == ["a/x: axisLabels", "a/x: dvtHosted", "a/x: chips"]
    assert "8" in problems[0] and "7" in problems[0]


def test_a_chip_or_a_hosted_slide_that_the_row_does_not_record_fails_and_a_recorded_one_that_vanished_fails():
    assert compare_ledger({"a/x": replace(BASE, dvt_hosted=True)}, _ledger(a__x={"axisLabels": 7}))
    assert compare_ledger({"a/x": BASE}, _ledger(a__x={"axisLabels": 7, "dvtHosted": True}))
    assert compare_ledger({"a/x": BASE}, _ledger(a__x={"axisLabels": 7, "chips": ["chip:a"]}))
    assert compare_ledger({"a/x": replace(BASE, chips=("chip:a", "chip:b"))}, _ledger(a__x={"axisLabels": 7, "chips": ["chip:b", "chip:a"]})) == []


def test_a_malformed_row_fails_instead_of_being_skipped():
    assert compare_ledger({"a/x": BASE}, _ledger(a__x={"labels": 7}))
    assert compare_ledger({"a/x": BASE}, _ledger(a__x={"axisLabels": 7, "extra": 1}))
    assert compare_ledger({"a/x": BASE}, _ledger(a__x={}))


def test_a_scene_and_an_svg_that_disagree_on_axis_labels_break_the_relation():
    assert relation_problems({"a/x": replace(BASE, svg_axis_labels=6)}) == ["a/x: the Scene has 7 axis labels, the SVG draws 6"]
    assert relation_problems({"a/x": BASE}) == []


def test_a_row_is_written_as_the_ledger_stores_it():
    assert format_row("a/x", BASE) == "a/x: {axisLabels: 7}"
    assert format_row("a/x", replace(BASE, dvt_hosted=True)) == "a/x: {axisLabels: 7, dvtHosted: true}"
