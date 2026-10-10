"""Real final Layout composition against an independent explicit-window oracle."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.layout.surface_geometry import coordinate_for_date
from chrona.presentation.layout.surface_marks import compose_surface_marks
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection, WindowMode
from chrona.usecases.warning_ledger import collect_render_warnings
from chrona.usecases.diagnostic_messages import describe_warning
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request


def _compose(*, fraction=None, window=(date(2026, 1, 5), date(2026, 1, 9)),
             mode=WindowMode.EXPLICIT, summaries=False):
    request = _axis_request(())
    items = tuple(ReviewItem(
        name, name, "span", {"start": date(2026, 1, start), "end": date(2026, 1, end)},
        None, None, ("planned",), item_id=name,
        planned_progress=fraction if name == "across" else None,
    ) for name, start, end in (("before", 1, 3), ("across", 1, 11), ("after", 10, 12)))
    rows = tuple(ReviewRowProjection(f"row-{item.object_id}", item.title, "group", item.item_id,
                                     (item,), rollup_presentation="bar") for item in items) if summaries else ()
    projection = ReviewProjection(items, window, (), (), window_mode=mode, rows=rows)
    content = replace(request.surface_content, progress_fill_source="planned" if fraction is not None else None)
    base = prepare_surface_base(replace(request, projection=projection, surface_content=content))
    return base, compose_surface_marks(base, lane_owner=lambda _row, _item: None)


def test_final_marks_omit_outside_sources_and_complete_across_contour_and_original_ports():
    base, batch = _compose()
    assert tuple(mark.source_ref for mark in batch.marks) == ("across",)
    mark = batch.marks[0]
    assert mark.paint_clip is not None
    assert mark.start_port is mark.end_port is None
    assert float(mark.bounds.inline) == pytest.approx(coordinate_for_date(date(2026, 1, 5), base.scale))
    assert float(mark.bounds.inline + mark.bounds.inline_size) == pytest.approx(
        coordinate_for_date(date(2026, 1, 9), base.scale))
    x, y, width, height = mark.paint_clip.bounds
    assert mark.path_commands
    assert all(x <= px <= x + width and y <= py <= y + height
               for command in mark.path_commands for px, py in command.points)
    original = batch.window_marks[0].original
    assert original.bounds.inline < mark.bounds.inline
    assert original.bounds.inline + original.bounds.inline_size > mark.bounds.inline + mark.bounds.inline_size
    assert original.paint_clip is None
    assert base.request.projection.items[1].planned["start"] == date(2026, 1, 1)
    assert batch.diagnostics.count("W_LAYOUT_OUTSIDE_WINDOW:table-timeline") == 1
    warning = next(item for item in batch.diagnostic_provenance
                   if item.diagnostic == "W_LAYOUT_OUTSIDE_WINDOW:table-timeline")
    assert tuple(subject.source_ref for subject in warning.subjects) == (
        "/objects/across", "/objects/after", "/objects/before")


def test_progress_uses_original_fraction_and_intersects_visible_notched_host():
    base, batch = _compose(fraction=.6)
    assert len(batch.progress_shapes) == 1
    progress = batch.progress_shapes[0]
    host = batch.marks[0]
    assert progress.kind == "Symbol" and progress.path_commands
    assert progress.paint_clip == host.paint_clip
    # 60% of Jan 1..11 ends Jan 7, not 60% of the shortened Jan 5..9 host.
    right = max(px for command in progress.path_commands for px, _ in command.points)
    assert right == pytest.approx(coordinate_for_date(date(2026, 1, 7), base.scale))
    x, y, width, height = progress.paint_clip.bounds
    assert all(x <= px <= x + width and y <= py <= y + height
               for command in progress.path_commands for px, py in command.points)


def test_progress_ending_before_visible_host_is_intentionally_unpainted():
    _, batch = _compose(fraction=.2)
    assert len(batch.marks) == 1
    assert batch.progress_shapes == ()


def test_fully_containing_explicit_window_preserves_final_mark_and_progress_values():
    window = (date(2026, 1, 1), date(2026, 1, 15))
    _, explicit = _compose(window=window, fraction=.6)
    _, derived = _compose(window=window, fraction=.6, mode=WindowMode.SELECTED_PLANNED)
    assert explicit.marks == derived.marks
    assert explicit.progress_shapes == derived.progress_shapes
    assert all(mark.paint_clip is None for mark in explicit.marks)
    assert not any("W_LAYOUT_OUTSIDE_WINDOW" in diagnostic for diagnostic in explicit.diagnostics)
    assert not any("W_LAYOUT_OUTSIDE_WINDOW" in diagnostic for diagnostic in derived.diagnostics)


def test_explicit_final_composition_cannot_fall_back_to_raw_source_geometry():
    base, _ = _compose()
    invalid = replace(base, request=replace(base.request, mark_visibility_index=None))
    with pytest.raises(LayoutError, match="missing-visibility-index"):
        compose_surface_marks(invalid, lane_owner=lambda _row, _item: None)


def test_outside_warning_transport_names_exact_objects_once_with_actionable_cause():
    _, batch = _compose()
    records = collect_render_warnings(
        surface_diagnostics=batch.diagnostics, surface_provenance=batch.diagnostic_provenance,
        tabular_warnings=(), glyph_warnings=(), fit_warnings=(), perceptibility_warnings=(),
        scale_collisions=(), attachment_warnings=(),
    )
    outside = tuple(record for record in records if record.payload["code"] == "W_LAYOUT_OUTSIDE_WINDOW")
    assert len(outside) == 1
    payload = outside[0].payload
    assert tuple(subject["sourceRef"] for subject in payload["sourceSubjects"]) == (
        "/objects/across", "/objects/after", "/objects/before")
    text = describe_warning(payload)
    assert "explicit window" in text.cause
    assert "source data is unchanged" in text.cause
    assert all(ref in text.subject for ref in ("/objects/across", "/objects/after", "/objects/before"))


def test_summary_uses_same_clipped_contour_rule_without_inventing_mark_or_ports():
    base, batch = _compose(summaries=True)
    assert tuple(shape.source_ref for shape in batch.summary_shapes) == ("across",)
    summary = batch.summary_shapes[0]
    assert summary.kind == "Symbol" and summary.paint_clip is not None
    assert summary.path_commands
    x, y, width, height = summary.paint_clip.bounds
    assert all(x <= px <= x + width and y <= py <= y + height
               for command in summary.path_commands for px, py in command.points)
    assert float(summary.bounds.inline) == pytest.approx(coordinate_for_date(date(2026, 1, 5), base.scale))
    assert float(summary.bounds.inline + summary.bounds.inline_size) == pytest.approx(
        coordinate_for_date(date(2026, 1, 9), base.scale))


def test_containing_summary_retains_existing_geometry_and_has_no_clip():
    window = (date(2026, 1, 1), date(2026, 1, 15))
    _, explicit = _compose(summaries=True, window=window)
    _, derived = _compose(summaries=True, window=window, mode=WindowMode.SELECTED_PLANNED)
    assert explicit.summary_shapes == derived.summary_shapes
    assert len(explicit.summary_shapes) == 3
    assert all(shape.kind == "Rect" and shape.paint_clip is None for shape in explicit.summary_shapes)
