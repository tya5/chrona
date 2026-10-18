"""Aggregate automatic-row name loss from accepted Layout placements."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_completion import SurfaceLayoutComposition
from chrona.presentation.layout.surface_quality import SurfacePlacement, TextPlacement
from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
from chrona.presentation.model.projection import ReviewItem, ReviewRowProjection
from chrona.presentation.layout.surface_row_identity import complete_row_identity_warning


def _item(object_id):
    return ReviewItem(object_id, object_id.title(), "span", {}, None, None, (), item_id=object_id)


def _row(row_id, *object_ids):
    items = tuple(_item(object_id) for object_id in object_ids)
    return ReviewRowProjection(row_id, row_id, "", row_id, items)


def _suppressed_label(object_id, placement_id=None):
    placement_id = placement_id or f"member-label:{object_id}"
    return TextPlacement(placement_id, object_id, object_id.title(), Rect(0, 0, 10, 10), "text",
                         overflow="suppressed", required=False, semantic_id="memberLabel")


def _composition(rows, suppressed_sources, *, other_diagnostics=()):
    text = tuple(_suppressed_label(source, f"member-label:{source}:{index}")
                 for index, source in enumerate(suppressed_sources))
    per_label = tuple(f"W_LAYOUT_LABEL_SUPPRESSED:{item.placement_id}" for item in text)
    placement = SurfacePlacement(
        text=text,
        diagnostics=(*other_diagnostics, *per_label),
        info_diagnostics=((SuppressedPlotLabels("table-timeline", len(text)),) if text else ()),
    )
    placement.assert_valid()
    return SurfaceLayoutComposition(placement, tuple(rows), (), ())


def _identity_warnings(composition):
    return tuple(item for item in composition.placement.diagnostics
                 if item.startswith("W_LAYOUT_ROW_IDENTITY_MISSING:"))


def test_counts_distinct_ordinary_rows_not_suppressed_label_occurrences():
    composition = _composition(
        (_row("row-a", "a1", "a2"), _row("row-b", "b")),
        ("a1", "a2", "b"),
        other_diagnostics=("W_LAYOUT_OTHER:keep",),
    )

    completed = complete_row_identity_warning(
        composition, row_mode="automatic", has_table_columns=False, name_selected=True)

    assert _identity_warnings(completed) == ("W_LAYOUT_ROW_IDENTITY_MISSING:count=2",)
    assert completed.placement.diagnostics[:1] == ("W_LAYOUT_OTHER:keep",)
    assert sum(item.startswith("W_LAYOUT_LABEL_SUPPRESSED:")
               for item in completed.placement.diagnostics) == 3
    assert tuple(item for item in completed.placement.info_diagnostics
                 if isinstance(item, SuppressedPlotLabels)) == (SuppressedPlotLabels("table-timeline", 3),)


@pytest.mark.parametrize(
    ("row_mode", "has_table_columns", "name_selected"),
    (("explicit", False, True), ("lanes", False, True),
     ("automatic", True, True), ("automatic", False, False)),
)
def test_identity_warning_is_gated_by_automatic_rows_missing_name_carrier(
        row_mode, has_table_columns, name_selected):
    composition = _composition((_row("row-a", "a"),), ("a",))

    completed = complete_row_identity_warning(
        composition, row_mode=row_mode, has_table_columns=has_table_columns,
        name_selected=name_selected)

    assert completed is composition


def test_title_column_gate_does_not_replace_layout_per_label_diagnostics():
    composition = _composition((_row("row-a", "a"),), ("a",))

    completed = complete_row_identity_warning(
        composition, row_mode="automatic", has_table_columns=True, name_selected=True)

    assert completed is composition
    assert completed.placement.diagnostics == composition.placement.diagnostics


def test_temporal_window_absence_count_alone_does_not_trigger_room_warning():
    # This real completion has three outside-window name absences in the legacy
    # aggregate count, but no spatially suppressed TextPlacement.
    from chrona.presentation.layout.surface_composer import compose_surface_layout
    from tests.unit.chrona.presentation.layout.test_window_label_composition import _request

    request = _request()
    request = replace(request, projection=replace(
        request.projection, window=(date(2026, 1, 15), date(2026, 1, 20))))
    composition = compose_surface_layout(request)
    placement = composition.placement
    assert len(placement.window_label_absences) == 3
    assert tuple(item for item in placement.info_diagnostics
                 if isinstance(item, SuppressedPlotLabels)) == (SuppressedPlotLabels("table-timeline", 3),)
    assert not any(item.semantic_id == "memberLabel" and item.overflow == "suppressed"
                   for item in placement.text)

    completed = complete_row_identity_warning(
        composition, row_mode="automatic", has_table_columns=False, name_selected=True)

    assert completed is composition
    assert _identity_warnings(completed) == ()
