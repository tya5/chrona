from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.surface_mark_visibility import build_item_mark_visibility_index
from chrona.presentation.layout.lane_window_marks import complete_lane_window_handoff
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import SurfacePlacement
from chrona.presentation.layout.surface_preparation import timeline_content_block_requirement
from chrona.presentation.layout.window_row_admission import (
    complete_window_row_admission, geometry_rows, geometry_surface_content, geometry_table,
)
from chrona.presentation.model.projection import (
    ReviewItem, ReviewProjection, ReviewRowProjection, WindowMode,
)
from chrona.presentation.model.surface_content import (
    SurfaceContentInput, TableContent, TableCellContent, TableRowLevel,
)
from tests.unit.chrona.presentation.layout.test_lane_item_footprints import _window_footprint_fixture


START = date(2026, 3, 10)
END = date(2026, 3, 20)


def _item(object_id, start, finish):
    return ReviewItem(
        object_id, object_id, "span", {"start": start, "end": finish}, None, None,
        ("planned",), item_id=object_id, source_kind="primary",
    )


def _admission(*, outside="omit", mode=WindowMode.EXPLICIT):
    outside_item = _item("outside", date(2026, 3, 1), date(2026, 3, 5))
    retained_item = _item("retained", date(2026, 3, 15), date(2026, 3, 25))
    outside_row = ReviewRowProjection("row-out", "Outside", "old", "outside", (outside_item,))
    retained_row = ReviewRowProjection("row-in", "Retained", "current", "retained", (retained_item,))
    projection = ReviewProjection(
        (outside_item, retained_item), (START, END), (), (), rows=(outside_row, retained_row),
        window_mode=mode, group_order=("old", "current"), window_outside=outside,
    )
    index = build_item_mark_visibility_index(projection, as_of=None)
    return projection, index, complete_window_row_admission(projection, index)


def test_admission_masks_only_geometry_and_keeps_exact_source_absence():
    projection, index, admission = _admission()

    assert admission.omitted_row_reasons == {"row-out": "outside-window"}
    assert tuple(row.row_id for row in geometry_rows(projection.rows, admission)) == ("row-in",)
    proof = admission.omission_for(next(key for key in index.entries if key.container_id == "row-out"))
    assert proof is not None
    assert (proof.row_id, proof.reason, proof.source_ref) == (
        "row-out", "outside-window", "/projection/rows/row-out/items/outside")
    assert tuple(projection.group_order) == ("old", "current")
    assert tuple(row.row_id for row in projection.rows) == ("row-out", "row-in")


def test_table_geometry_uses_canonical_row_ids_and_preserves_source_columns():
    _projection, _index, admission = _admission()
    table = TableContent(
        (),
        (TableCellContent("row-out", "name", "Outside", "tableCell"),
         TableCellContent("row-in", "name", "Retained", "tableCell")),
        (("row-out", "name", "outside", True), ("row-in", "name", "retained", True)),
        "name",
        (TableRowLevel(("row-out", "outside"), True),
         TableRowLevel(("row-in", "retained"), True)),
    )

    masked = geometry_table(table, admission)

    assert tuple(cell.object_id for cell in masked.cells) == ("row-in",)
    assert masked.cell_objects == (("row-in", "name", "retained", True),)
    assert masked.row_levels == (TableRowLevel(("row-in", "retained"), True),)
    assert masked.columns is table.columns


def test_keep_policy_returns_original_geometry_inputs_by_identity():
    projection, _index, admission = _admission(outside="keep")
    table = TableContent((), (), (), None, ())

    assert geometry_rows(projection.rows, admission) is projection.rows
    assert geometry_table(table, admission) is table


def test_relative_window_uses_the_same_bounded_row_admission_contract():
    projection, _index, admission = _admission(mode=WindowMode.RELATIVE)

    assert admission.omit_outside
    assert tuple(row.row_id for row in geometry_rows(projection.rows, admission)) == ("row-in",)


def test_legacy_auto_rows_use_canonical_identity_for_window_masking():
    outside = _item("auto-outside", date(2026, 3, 1), date(2026, 3, 5))
    projection = ReviewProjection(
        (outside,), (START, END), (), (), window_mode=WindowMode.EXPLICIT,
        window_outside="omit",
    )
    index = build_item_mark_visibility_index(projection, as_of=None)
    admission = complete_window_row_admission(projection, index)

    requirement = timeline_content_block_requirement(
        projection=projection, group_presentation="none", metric_values={
            "timeline.row.minBlockSize": Decimal("1"),
            "timeline.row.paddingBlock": Decimal("0"),
            "timeline.mark.blockSize": Decimal("1"),
        }, row_admission=admission,
    )

    assert requirement == Decimal(0)
    assert not projection.has_rows
    assert admission.omitted_row_reasons == {"auto-outside": "outside-window"}


def test_normalized_surface_table_cells_are_filtered_by_row_not_object_source():
    _projection, _index, admission = _admission()
    content = SurfaceContentInput(
        table_columns=(),
        table_cells=(TableCellContent("row-out", "name", "Outside", "tableCell"),
                     TableCellContent("row-in", "name", "Retained", "tableCell")),
        table_cell_objects=(
            ("row-out", "name", "outside", True),
            ("row-in", "name", "retained", True),
        ),
        relations=(), annotations=(), show_member_labels=False,
        label_placement="none", label_content=(), label_side="auto", label_overflow="suppress",
        relation_overflow="suppress", group_presentation="none", axis_tiers=(),
        axis_fiscal_start_month=1, as_of=None, as_of_label="", annotation_numbered=False,
        calendar_closed=(), calendar_exceptions=(), notes=(), legend_entries=(), coverage_text="",
        summary=None, template_values=(), group_details=(), milestones=(),
        observation_columns=(), observation_rows=(),
    )

    masked = geometry_surface_content(content, admission)

    assert tuple(cell.object_id for cell in masked.table_cells) == ("row-in",)
    assert masked.table_cell_objects == (("row-in", "name", "retained", True),)
    assert geometry_surface_content(masked, admission) is masked


def test_omitted_lane_absences_require_the_matching_row_source_proof():
    projection, _old_index, _kwargs = _window_footprint_fixture(all_outside=True)
    projection = replace(projection, window_outside="omit")
    index = build_item_mark_visibility_index(projection, as_of=None)
    admission = complete_window_row_admission(projection, index)
    absences, omitted_rows, row_absences = complete_lane_window_handoff(
        (), projection=projection, as_of=None, visibility_index=index,
        row_admission=admission,
    )

    assert omitted_rows == {"lane"}
    assert absences and all(item.row_omission_proof is not None for item in absences)
    assert len(row_absences) == 2
    SurfacePlacement(lane_window_absences=absences,
                     lane_window_row_absences=row_absences).assert_valid()

    forged = replace(absences[0], row_omission_proof=None)
    with pytest.raises(ValueError, match="E_LAYOUT_WINDOW_CLIP"):
        SurfacePlacement(lane_window_absences=(forged, *absences[1:]),
                         lane_window_row_absences=row_absences).assert_valid()
    if len(absences) > 1:
        with pytest.raises(LayoutError, match="invalid-row-omission-proof"):
            replace(absences[0], row_omission_proof=absences[1].row_omission_proof)
