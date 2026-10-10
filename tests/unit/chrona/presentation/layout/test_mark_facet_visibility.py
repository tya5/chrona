from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from chrona.presentation.layout.semantic_mark_facets import (
    ItemMarkFacetSelection,
    LogicalMarkFacet,
    MarkFacetAbsence,
)
from chrona.presentation.model.projection import WindowMode
from chrona.presentation.layout.mark_facet_visibility import complete_item_visibility
from chrona.presentation.layout.model import LayoutError


D1 = date(2026, 2, 1)
D2 = date(2026, 2, 2)
D3 = date(2026, 2, 3)
D4 = date(2026, 2, 4)
D5 = date(2026, 2, 5)
D6 = date(2026, 2, 6)
D7 = date(2026, 2, 7)


def _selection(*facets, source_kind="combined"):
    return ItemMarkFacetSelection(
        source_kind=source_kind,
        as_of=D4,
        missing_actual_eligible=True,
        facets=tuple(facets),
        diagnostics=(),
        absences=(MarkFacetAbsence("actual", "no-selected-observation"),),
    )


def _visible(selection, mode=WindowMode.EXPLICIT, start=D2, end=D6):
    return complete_item_visibility(
        selection,
        instance_id="row-1:item-1",
        source_ref="item-1",
        window_mode=mode,
        window_start=start,
        window_end=end,
    )


def _one(source, *, mode=WindowMode.EXPLICIT, start=D2, end=D6):
    result = _visible(_selection(source), mode=mode, start=start, end=end)
    assert result.selection.facets == (source,)
    assert result.instance_id == "row-1:item-1"
    assert result.source_ref == "item-1"
    assert len(result.facets) == 1
    visible = result.facets[0]
    assert visible.source is source
    return visible


def _span(start, finish, *, facet="planned", semantic_id="planned"):
    return LogicalMarkFacet(facet, semantic_id, "span", start=start, finish=finish)


@pytest.mark.parametrize(
    ("source", "window_start", "window_end", "expected"),
    [
        (_span(D3, D5), D2, D6,
         ("contained", D3, D5, False, False, True, True)),
        (_span(D1, D5), D2, D6,
         ("clipped", D2, D5, True, False, False, True)),
        (_span(D3, D7), D2, D6,
         ("clipped", D3, D6, False, True, True, False)),
        (_span(D1, D7), D2, D6,
         ("clipped", D2, D6, True, True, False, False)),
        (_span(D2, D6), D2, D6,
         ("contained", D2, D6, False, False, True, True)),
    ],
)
def test_explicit_span_intersection_and_original_endpoint_ports(
        source, window_start, window_end, expected):
    visible = _one(source, start=window_start, end=window_end)
    assert (
        visible.disposition, visible.visible_start, visible.visible_finish,
        visible.cut_start, visible.cut_finish,
        visible.start_port_visible, visible.end_port_visible,
    ) == expected
    assert visible.visible_at is None


@pytest.mark.parametrize(
    ("source", "window_start", "window_end"),
    [
        (_span(D1, D2), D2, D6),  # ends exactly where the window begins
        (_span(D6, D7), D2, D6),  # begins exactly where the window ends
        (_span(D1, D2), D3, D6),
        (_span(D6, D7), D2, D5),
    ],
)
def test_disjoint_or_boundary_touching_spans_are_omitted_without_ports(
        source, window_start, window_end):
    visible = _one(source, start=window_start, end=window_end)
    assert (visible.disposition, visible.visible_start, visible.visible_finish) == (
        "omitted", None, None
    )
    assert not visible.start_port_visible and not visible.end_port_visible
    assert not visible.cut_start and not visible.cut_finish


@pytest.mark.parametrize(
    ("at", "window_start", "window_end", "disposition", "visible_at"),
    [
        (D2, D2, D6, "contained", D2),
        (D3, D2, D6, "contained", D3),
        (D6, D2, D6, "omitted", None),
        (D1, D2, D6, "omitted", None),
    ],
)
def test_points_use_the_half_open_explicit_window(at, window_start, window_end,
                                                   disposition, visible_at):
    source = LogicalMarkFacet("planned", "planned", "point", at=at)
    visible = _one(source, start=window_start, end=window_end)
    assert (visible.disposition, visible.visible_at) == (disposition, visible_at)
    assert visible.visible_start is None and visible.visible_finish is None
    assert visible.start_port_visible is (visible_at is not None)
    assert visible.end_port_visible is (visible_at is not None)


@pytest.mark.parametrize(
    ("at", "window_start", "window_end", "disposition", "visible_at"),
    [
        (D2, D2, D6, "contained", D2),
        (D6, D2, D6, "omitted", None),
    ],
)
def test_due_end_missing_actual_retains_span_shape_but_uses_anchor_visibility(
        at, window_start, window_end, disposition, visible_at):
    source = LogicalMarkFacet("missing-actual", "missing-actual", "span",
                              geometry="end-tick", start=at, finish=at)
    visible = _one(source, start=window_start, end=window_end)
    assert source.shape == "span"
    assert (visible.disposition, visible.visible_at) == (disposition, visible_at)
    assert visible.start_port_visible is (visible_at is not None)
    assert visible.end_port_visible is (visible_at is not None)


@pytest.mark.parametrize(
    "mode",
    (WindowMode.SELECTED_PLANNED, WindowMode.SELECTED_COMPARISON),
)
def test_derived_windows_preserve_original_spans_and_ports_without_clipping(mode):
    source = _span(D1, D7, facet="actual", semantic_id="actual")
    visible = _one(source, mode=mode, start=D2, end=D6)
    assert (visible.disposition, visible.visible_start, visible.visible_finish) == (
        "contained", D1, D7
    )
    assert not visible.cut_start and not visible.cut_finish
    assert visible.start_port_visible and visible.end_port_visible
    assert visible.source is source


def test_derived_window_preserves_original_point():
    source = LogicalMarkFacet("planned", "planned", "point", at=D7)
    visible = _one(source, mode=WindowMode.SELECTED_PLANNED, start=D2, end=D6)
    assert (visible.disposition, visible.visible_at) == ("contained", D7)
    assert visible.start_port_visible and visible.end_port_visible


def test_facet_closure_is_independent_and_retains_selection_without_mutation():
    planned = _span(D1, D5)
    actual = _span(D3, D7, facet="actual", semantic_id="actual")
    selection = _selection(planned, actual)
    result = complete_item_visibility(selection, instance_id="instance", source_ref="object",
                                      window_mode=WindowMode.EXPLICIT,
                                      window_start=D2, window_end=D6)
    assert [(entry.source.facet, entry.disposition) for entry in result.facets] == [
        ("planned", "clipped"), ("actual", "clipped")
    ]
    assert result.selection is selection
    assert selection.facets == (planned, actual)
    with pytest.raises(FrozenInstanceError):
        result.instance_id = "changed"
    with pytest.raises(FrozenInstanceError):
        result.facets[0].cut_start = False


@pytest.mark.parametrize("finish", (D3, D2))
def test_nonpositive_actual_interval_fails_closed_without_point_conversion(finish):
    source = _span(D3, finish, facet="actual", semantic_id="actual")
    with pytest.raises(LayoutError) as caught:
        _one(source)
    error = caught.value
    assert error.diagnostic_id == "E_LAYOUT_WINDOW_CLIP"
    assert error.detail == (
        "source='item-1'; facet='actual'; stage=visibility; "
        "reason=nonpositive-source-interval"
    )
    assert (source.start, source.finish, source.shape) == (D3, finish, "span")


@pytest.mark.parametrize("mode", (WindowMode.SELECTED_PLANNED, WindowMode.SELECTED_COMPARISON))
def test_nonpositive_actual_does_not_change_the_out_of_scope_derived_path(mode):
    source = _span(D3, D3, facet="actual", semantic_id="actual")
    visible = _one(source, mode=mode)
    assert (visible.source, visible.visible_start, visible.visible_finish) == (source, D3, D3)


def test_invalid_source_diagnostic_copy_is_bounded():
    source = _span(D3, D3, facet="actual", semantic_id="actual")
    with pytest.raises(LayoutError) as caught:
        complete_item_visibility(_selection(source), instance_id="instance",
                                 source_ref="x" * 10000, window_mode=WindowMode.EXPLICIT,
                                 window_start=D2, window_end=D6)
    assert len(caught.value.detail) < 180
    assert "…" in caught.value.detail


def test_open_actual_keeps_original_cutoff_and_end_treatment_when_clipped():
    source = LogicalMarkFacet("actual", "actual", "open-span", geometry="open-span",
                              start=D1, finish=D7, end_treatment="open")
    visible = _one(source)
    assert (visible.visible_start, visible.visible_finish) == (D2, D6)
    assert (visible.source.start, visible.source.finish, visible.source.end_treatment) == (D1, D7, "open")


@pytest.mark.parametrize("start,finish", ((None, D5), (D3, None)))
def test_incomplete_source_facet_is_not_silently_admitted(start, finish):
    source = _span(start, finish, facet="actual", semantic_id="actual")
    with pytest.raises(LayoutError, match="reason=source-date-unavailable"):
        _one(source)
