"""Synthetic contracts for the #1936 label and grouping controls."""
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from chrona.core.forecast import ForecastItem
from chrona.presentation.contracts.resources import (
    ClosureIdentity, TableColumn, ViewComparison, ViewContract, ViewInput,
    ViewRow, ViewRowItem, ViewRows, ViewVisibility, ViewWindow, freeze, parse_contract,
)
from chrona.presentation.model.projection import (
    ForecastComparisonFact, ReviewItem, ReviewProjection, build_review_projection,
    omit_zero_finish_delta,
)
from chrona.presentation.review.v05_content import normalize_v05_surface_content, normalize_v05_table_content
from chrona.presentation.model.surface_content import SummaryContent
from chrona.presentation.table_presentation import CellAffix, ColumnAffixes
from chrona.resources import safe_load, schema_validator
from chrona.scheduling.scheduler import ReferenceScheduler


ROOT = Path(__file__).resolve().parents[4]


def _view(*, baseline_labels="auto", baseline_marks=None, rows=None, columns=(), labels=False):
    return ViewInput(
        None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison("snapshot", "optional", None, "calendar-days", (),
                       baseline_marks=baseline_marks, baseline_labels=baseline_labels),
        ViewVisibility(freeze(labels) if isinstance(labels, dict) else labels, "none", "none"),
        tuple(columns), (), rows or ViewRows("automatic", ()), None, (), None, None, None,
    )


def _scheduled(project):
    result = ReferenceScheduler().schedule(project)
    assert result.ok, result.diagnostics
    return result.placements


def _project(*, span_start="2026-01-05", span_end="2026-01-12", extra=False):
    objects = {"span": {"type": "task", "schedule": {
        "mode": "fixed-span", "start": span_start, "end": span_end}}}
    if extra:
        objects["removed"] = {"type": "gate", "schedule": {
            "mode": "fixed-point", "at": "2026-01-09"}}
    return {"version": "timeline/v0.7", "project": {"id": "control"}, "objects": objects}


def test_view_and_profile_schemas_admit_new_properties_without_changing_defaults():
    view = safe_load((ROOT / "tests/fixtures/controller-z/views/baseline-ghosts.yaml").read_bytes())
    view["body"]["comparison"]["baselineLabels"] = "none"
    view["body"]["grouping"]["presentation"] = "header"
    view["body"]["grouping"]["headerPlacement"] = "timeline"
    view["body"]["visibility"]["labels"]["omitZeroDelta"] = True
    schema_validator("view-v0.28.schema.yaml").validate(view)
    contract = parse_contract(
        ClosureIdentity("view", view["id"], "test", "sha256:" + "0" * 64), view)
    assert isinstance(contract, ViewContract)
    assert contract.view.comparison.baseline_labels == "none"
    assert contract.view.grouping.header_placement == "timeline"

    non_header = safe_load((ROOT / "tests/fixtures/controller-z/views/baseline-ghosts.yaml").read_bytes())
    non_header["body"]["grouping"]["presentation"] = "band"
    non_header["body"]["grouping"]["headerPlacement"] = "timeline"
    schema_validator("view-v0.28.schema.yaml").validate(non_header)
    assert parse_contract(ClosureIdentity("view", non_header["id"], "test", "sha256:" + "1" * 64),
                          non_header).view.grouping.header_placement == "timeline"

    defaults = {"comparison": {"baselineLabels": "none"},
                "grouping": {"headerPlacement": "timeline"}}
    from chrona.presentation.contracts.view_defaults import merge_view_defaults
    merged = merge_view_defaults(
        {"version": "chrona/view/v0.28", "kind": "view", "id": "test",
         "body": {"comparison": {"actual": "optional", "facets": []},
                  "grouping": {"by": "field", "field": "owner", "missing": "Unset"}}},
        defaults,
    )
    assert merged["body"]["comparison"]["baselineLabels"] == "none"
    assert merged["body"]["grouping"]["headerPlacement"] == "timeline"

    bad = safe_load((ROOT / "tests/fixtures/controller-z/views/baseline-ghosts.yaml").read_bytes())
    bad["body"]["comparison"]["baselineLabels"] = "hide"
    with pytest.raises(Exception):
        schema_validator("view-v0.28.schema.yaml").validate(bad)


def test_baseline_labels_none_keeps_paired_ghost_but_removes_only_its_label_eligibility():
    current, snapshot = _project(), _project(span_start="2026-01-06", span_end="2026-01-13")
    auto = _view(baseline_marks="ghost")
    none = replace(auto, comparison=replace(auto.comparison, baseline_labels="none"))
    projections = [build_review_projection(
        current, _scheduled(current), view, None,
        snapshot_project=snapshot, snapshot_placements=_scheduled(snapshot))
        for view in (auto, none)]
    for projection, ghost_eligible in zip(projections, (True, False), strict=True):
        paired = projection.rows[0].items
        assert [item.source_kind for item in paired] == ["combined", "snapshot"]
        assert paired[0].member_label_eligible is True
        assert paired[1].member_label_eligible is ghost_eligible
        assert paired[1].planned["start"] == date(2026, 1, 6)


def test_baseline_labels_none_does_not_remove_explicit_or_removed_only_identity_labels():
    current, snapshot = _project(), _project(extra=True)
    explicit = _view(baseline_labels="none", rows=ViewRows("explicit", (
        ViewRow("span-row", None, 0, None, None, "primary", (
            ViewRowItem("primary", "primary", "span", "shared"),
            ViewRowItem("snapshot", "snapshot", "span", "shared"),
        )),
    )))
    explicit_projection = build_review_projection(
        current, _scheduled(current), explicit, None,
        snapshot_project=snapshot, snapshot_placements=_scheduled(snapshot))
    explicit_ghost = next(item for item in explicit_projection.rows[0].items
                          if item.source_kind == "snapshot")
    assert explicit_ghost.member_label_eligible

    automatic = replace(explicit, rows=ViewRows("automatic", ()),
                        comparison=replace(explicit.comparison, baseline_marks="ghost"))
    removed_projection = build_review_projection(
        current, _scheduled(current), automatic, None,
        snapshot_project=snapshot, snapshot_placements=_scheduled(snapshot))
    removed = next(row for row in removed_projection.rows if row.row_id == "removed")
    assert len(removed.items) == 1
    assert removed.items[0].source_kind == "snapshot"
    assert removed.items[0].member_label_eligible


def test_table_zero_omit_clears_entire_display_but_keeps_fact_semantic_and_other_states():
    column = TableColumn(
        "delta", freeze({"facet": "finishDelta"}), "signedDays", "em-dash",
        zero="omit", affixes=ColumnAffixes(
            slip=CellAffix(suffix="!"), on_time=CellAffix(prefix="(", suffix=")"),
            missing=CellAffix(prefix="?")), priority="required")
    items = (
        ReviewItem("zero", "Zero", "task", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                   None, 0, ()),
        ReviewItem("behind", "Behind", "task", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                   None, 2, ()),
        ReviewItem("new", "New", "task", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                   None, None, (), new_vs_baseline=True, new_marker="new"),
    )
    projection = ReviewProjection(items, (date(2026, 1, 1), date(2026, 1, 3)), (), ())
    view = _view(columns=(column,))
    table = normalize_v05_table_content(
        projection, {}, view, actual_set={"body": {"asOf": "2026-01-03", "observations": []}})
    assert [cell.content for cell in table.cells] == ["", "+2d!", "?new"]
    assert table.cells[0].semantic_id == "tableVarianceOnTrack"
    assert table.cells[0].affix_prefix == table.cells[0].affix_suffix == ""
    assert table.cells[1].semantic_id == "tableVarianceBehind"


def test_table_zero_omit_also_removes_estimated_suffix_without_changing_required_fact():
    forecast = ForecastComparisonFact(
        ForecastItem({"start": date(2026, 1, 1), "finish": date(2026, 1, 3)}, completed=False), 0)
    item = ReviewItem("forecast", "Forecast", "task",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 3)}, None, 0, (), forecast=forecast)
    column = TableColumn("delta", freeze({"facet": "finishDelta"}), "signedDays", "em-dash",
                         zero="omit", affixes=ColumnAffixes(on_time=CellAffix(suffix="!")), priority="required")
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 4)), (), ())
    table = normalize_v05_table_content(projection, {}, _view(columns=(column,)))
    assert table.cells[0].content == ""
    assert table.cells[0].semantic_id == "tableVarianceOnTrack"
    assert table.cells[0].required and table.cells[0].estimated_delta


def test_plot_zero_omission_is_component_only_and_exact_integer_zero():
    zero = ReviewItem("zero", "Still visible", "task", {"end": date(2026, 1, 2)}, None, 0, ())
    nonzero = replace(zero, finish_delta=1)
    missing = replace(zero, finish_delta=None)
    assert omit_zero_finish_delta(zero, True)
    assert not omit_zero_finish_delta(nonzero, True)
    assert not omit_zero_finish_delta(missing, True)
    assert not omit_zero_finish_delta(zero, False)
    view = _view(labels={"placement": "plot", "content": ["title", "finishDelta"],
                         "omitZeroDelta": True})
    content = normalize_v05_surface_content(
        ReviewProjection((zero, nonzero), (date(2026, 1, 1), date(2026, 1, 3)), (), ()),
        {}, view, summary=SummaryContent(()))
    assert content.omit_zero_delta is True
    assert content.label_content == ("title", "finishDelta")
    assert content.show_member_labels
