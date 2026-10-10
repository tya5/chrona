from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from chrona.presentation.layout.mark_facet_visibility import (
    FacetDisposition, MarkFacetVisibility,
)
from chrona.presentation.layout.mark_geometry import complete_mark_window_geometry, SymbolPartPlacement
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.mark_facet_visibility import complete_item_visibility
from chrona.presentation.layout.path_geometry import open_span_path
from chrona.presentation.layout.semantic_mark_facets import LogicalMarkFacet, select_item_mark_facets
from chrona.presentation.layout.surface_quality import MarkPlacement, ScalePlacement, is_closed_stroke_contour
from chrona.presentation.model.projection import ReviewItem, WindowMode


D0 = date(2026, 1, 1)
SCALE = ScalePlacement("timeline", "axis", D0, D0 + timedelta(days=10), 0, 10, 0, 1)
PLOT = Rect(Decimal(0), Decimal(0), Decimal(10), Decimal(10))


def _mark(*, shape="span", end_treatment="closed"):
    return MarkPlacement(
        "planned:item", "item", Rect(Decimal(0), Decimal(2), Decimal(10), Decimal(4)),
        (0, 4), (10, 4), mark_shape=shape, corner_radius=1,
        path_commands=(open_span_path(inline=0, block=2, inline_size=10,
                                      block_size=4, radius=0)
                       if shape == "open-span" else ()),
        end_treatment=end_treatment,
    )


def _visibility(*, disposition, visible_start=None, visible_finish=None,
                cut_start=False, cut_finish=False, start_port=True, end_port=True,
                shape="span"):
    source = LogicalMarkFacet(
        "planned", "planned", shape, "open-span" if shape == "open-span" else "span",
        start=D0, finish=D0 + timedelta(days=10), end_treatment="open" if shape == "open-span" else "closed",
    )
    return MarkFacetVisibility(
        source, disposition, visible_start=visible_start, visible_finish=visible_finish,
        cut_start=cut_start, cut_finish=cut_finish,
        start_port_visible=start_port, end_port_visible=end_port,
    )


def test_contained_and_omitted_keep_source_mark_identity():
    mark = _mark()
    contained = complete_mark_window_geometry(
        mark, _visibility(disposition=FacetDisposition.CONTAINED), SCALE, PLOT)
    omitted = complete_mark_window_geometry(
        mark, _visibility(disposition=FacetDisposition.OMITTED), SCALE, PLOT)
    assert contained.original is mark and contained.visible is mark and contained.paint_clip is None
    assert omitted.original is mark and omitted.visible is None and omitted.paint_clip is None


def test_clipped_span_uses_date_host_closed_contour_and_only_original_ports():
    mark = _mark()
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED,
        visible_start=D0 + timedelta(days=2), visible_finish=D0 + timedelta(days=8),
        cut_start=True, cut_finish=True, start_port=False, end_port=False,
    )
    result = complete_mark_window_geometry(mark, visibility, SCALE, PLOT)
    assert result.original is mark and result.visible is not mark
    assert result.visibility is visibility
    assert result.visibility.source.start == D0
    assert result.visibility.source.finish == D0 + timedelta(days=10)
    assert result.visible is not None and result.paint_clip is not None
    assert result.visible.bounds == Rect(Decimal(2), Decimal(2), Decimal(6), Decimal(4))
    assert result.visible.start_port is None and result.visible.end_port is None
    assert result.visible.corner_radius == 0
    assert is_closed_stroke_contour(result.visible.path_commands)
    assert result.paint_clip.bounds == (0.0, 0.0, 10.0, 10.0)
    assert mark.bounds == Rect(Decimal(0), Decimal(2), Decimal(10), Decimal(4))
    assert mark.corner_radius == 1 and not mark.path_commands
    assert all(2 <= point[0] <= 8 and 2 <= point[1] <= 6
               for command in result.visible.path_commands for point in command.points)


def test_one_cut_preserves_original_rounded_opposite_edge_and_eligible_port():
    mark = _mark()
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED,
        visible_start=D0 + timedelta(days=2), visible_finish=D0 + timedelta(days=10),
        cut_start=True, start_port=False, end_port=True,
    )
    result = complete_mark_window_geometry(mark, visibility, SCALE, PLOT)
    assert result.visible is not None
    assert result.visible.start_port is None and result.visible.end_port == mark.end_port
    assert any(command.kind == "quadratic" and command.points[-1][0] == 10
               for command in result.visible.path_commands)
    assert all(2 <= point[0] <= 10 for command in result.visible.path_commands
               for point in command.points)


def test_open_span_symbol_part_uses_completed_contour_not_original_outside_geometry():
    original = _mark(shape="open-span", end_treatment="open")
    part = SymbolPartPlacement(original.path_commands, paint_mode="fill", paint_color="#123456")
    original = replace(original, symbol_parts=(part,))
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED, visible_start=D0 + timedelta(days=2),
        visible_finish=D0 + timedelta(days=8), cut_start=True, cut_finish=True,
        start_port=False, end_port=False, shape="open-span")
    completed = complete_mark_window_geometry(original, visibility, SCALE, PLOT)
    visible = completed.visible
    assert visible.symbol_parts[0].commands == visible.path_commands
    assert visible.symbol_parts[0].paint_mode == part.paint_mode
    assert visible.symbol_parts[0].paint_color == part.paint_color
    assert visible.symbol_parts[0].commands != part.commands
    assert all(2 <= px <= 8 for command in visible.symbol_parts[0].commands for px, _ in command.points)
    assert original.symbol_parts == (part,)


def test_narrow_visible_open_span_keeps_open_end_only_when_that_end_survives():
    mark = _mark(shape="open-span", end_treatment="open")
    open_visibility = _visibility(
        disposition=FacetDisposition.CLIPPED, visible_start=D0 + timedelta(days=2),
        visible_finish=D0 + timedelta(days=10), cut_start=True,
        start_port=False, end_port=True, shape="open-span",
    )
    retained = complete_mark_window_geometry(mark, open_visibility, SCALE, PLOT)
    assert retained.visible is not None
    assert retained.visible.mark_shape == "open-span" and retained.visible.end_treatment == "open"
    assert retained.visible.end_port == mark.end_port

    close_visibility = replace(open_visibility, visible_start=D0 + timedelta(days=8),
                               visible_finish=D0 + timedelta(days=9), cut_finish=True,
                               end_port_visible=False)
    closed = complete_mark_window_geometry(mark, close_visibility, SCALE, PLOT)
    assert closed.visible is not None
    assert closed.visible.mark_shape == "span" and closed.visible.end_treatment == "closed"
    assert closed.visible.end_port is None
    assert closed.visible.bounds.inline_size == Decimal(1)


def test_clipped_host_must_stay_inside_plot_and_errors_are_bounded():
    mark = _mark()
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED,
        visible_start=D0 + timedelta(days=2), visible_finish=D0 + timedelta(days=8),
        cut_start=True, cut_finish=True,
    )
    with pytest.raises(LayoutError) as error:
        complete_mark_window_geometry(mark, visibility, SCALE,
                                      Rect(Decimal(0), Decimal(0), Decimal(10), Decimal(5)))
    assert error.value.diagnostic_id == "E_LAYOUT_WINDOW_CLIP"
    assert error.value.path == "/layout/windowContour"
    assert "host-outside-plot" in error.value.detail


def test_actual_visibility_completion_flows_into_geometry_without_reselecting_dates():
    item = ReviewItem(
        "item", "Item", "span", {"start": D0, "end": D0 + timedelta(days=10)},
        None, None, ("planned",), item_id="item",
    )
    selection = select_item_mark_facets(item=item, source_kind="primary", as_of=None)
    visibility = complete_item_visibility(
        selection, instance_id="item", source_ref="/projection/items/item",
        window_mode=WindowMode.EXPLICIT,
        window_start=D0 + timedelta(days=2), window_end=D0 + timedelta(days=8),
    ).facets[0]
    result = complete_mark_window_geometry(_mark(), visibility, SCALE, PLOT)
    assert result.visibility is visibility
    assert result.visible is not None
    assert result.visible.bounds == Rect(Decimal(2), Decimal(2), Decimal(6), Decimal(4))
    assert result.visible.start_port is None and result.visible.end_port is None


def test_translated_plot_and_scale_complete_geometry_in_surface_coordinates():
    mark = replace(_mark(), bounds=Rect(Decimal(100), Decimal(22), Decimal(10), Decimal(4)),
                   start_port=(100, 24), end_port=(110, 24))
    scale = replace(SCALE, range_start=100, range_end=110, origin=100)
    plot = Rect(Decimal(100), Decimal(20), Decimal(10), Decimal(10))
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED,
        visible_start=D0 + timedelta(days=2), visible_finish=D0 + timedelta(days=8),
        cut_start=True, cut_finish=True, start_port=False, end_port=False,
    )
    result = complete_mark_window_geometry(mark, visibility, scale, plot)
    assert result.visible is not None and result.paint_clip is not None
    assert result.visible.bounds == Rect(Decimal(102), Decimal(22), Decimal(6), Decimal(4))
    assert result.paint_clip.bounds == (100.0, 20.0, 10.0, 10.0)
    assert all(102 <= point[0] <= 108 and 22 <= point[1] <= 26
               for command in result.visible.path_commands for point in command.points)


@pytest.mark.parametrize("bad_scale", [
    replace(SCALE, unit_ratio=True),
    replace(SCALE, origin=float("inf")),
])
def test_malformed_scale_is_a_bounded_window_geometry_error(bad_scale):
    mark = _mark()
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED,
        visible_start=D0 + timedelta(days=2), visible_finish=D0 + timedelta(days=8),
        cut_start=True, cut_finish=True,
    )
    with pytest.raises(LayoutError) as error:
        complete_mark_window_geometry(mark, visibility, bad_scale, PLOT)
    assert error.value.diagnostic_id == "E_LAYOUT_WINDOW_CLIP"
    assert "stage=geometry" in error.value.detail


def test_malformed_source_radius_is_a_bounded_window_geometry_error():
    mark = replace(_mark(), corner_radius="not-a-radius")
    visibility = _visibility(
        disposition=FacetDisposition.CLIPPED,
        visible_start=D0 + timedelta(days=2), visible_finish=D0 + timedelta(days=8),
        cut_start=True, cut_finish=True,
    )
    with pytest.raises(LayoutError) as error:
        complete_mark_window_geometry(mark, visibility, SCALE, PLOT)
    assert error.value.diagnostic_id == "E_LAYOUT_WINDOW_CLIP"
    assert error.value.path == "/layout/windowContour"
    assert "contour-operation-failed" in error.value.detail
