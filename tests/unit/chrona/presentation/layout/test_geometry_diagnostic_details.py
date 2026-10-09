"""Layout terminal/command diagnostics name operands without inspecting payloads."""
from __future__ import annotations

import pytest
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.profile import _nodes

from chrona.presentation.layout.surface_quality import (
    CapacitySourceEvidence, FitWarning, LaneEmissionFacet, LaneEmissionPlacement,
    LaneLabelSuppression, MarkerGeometry, PathCommand, PlacementDecision,
    RowPlacement, SurfacePlacement, TextPlacement, VisualRequest, annotation_presentation,
)


BOUNDS = Rect(Decimal(0), Decimal(10), Decimal(20), Decimal(30))


def test_profile_duplicate_node_names_actual_identifier():
    with pytest.raises(ValueError) as raised:
        _nodes({"id": "duplicate-77", "children": ({"id": "duplicate-77"},)})
    assert raised.value.diagnostic_id == "E_LAYOUT_NODE_DUPLICATE"
    assert "duplicate-77" in raised.value.detail


@pytest.mark.parametrize("make,code,operand", [
    (lambda: PathCommand("sentinel-command", ((0, 0),)), "E_LAYOUT_PATH_COMMAND_INVALID", "sentinel-command"),
    (lambda: PathCommand("quadratic", ((0, 0),)), "E_LAYOUT_PATH_COMMAND_INVALID", "has 1 points"),
    (lambda: PathCommand("move", (("private text", 0),)), "E_LAYOUT_PATH_COMMAND_INVALID", "str"),
    (lambda: MarkerGeometry((), 2, 4, 0, "fill"), "E_PRESENTATION_PRIMITIVE_INVALID", "outline_count=0"),
    (lambda: MarkerGeometry((PathCommand("move", ((0, 0),)),), -91, 4, 0, "fill"),
     "E_PRESENTATION_PRIMITIVE_INVALID", "head_length=-91"),
    (lambda: annotation_presentation("sentinel-purpose"), "E_PRESENTATION_ANNOTATION_PURPOSE", "sentinel-purpose"),
    (lambda: VisualRequest("label", (), "icon", side="sentinel-side"), "E_VIEW_VISUAL_REQUEST", "sentinel-side"),
    (lambda: VisualRequest("label", (), None, source_ref="/body/visuals/sentinel"), "E_VIEW_VISUAL_REQUEST", "/body/visuals/sentinel"),
])
def test_geometry_rejection_has_the_specific_operand(make, code, operand):
    with pytest.raises(ValueError) as raised:
        make()
    assert str(raised.value).startswith(code + ":") and operand in str(raised.value)
    assert "private text" not in str(raised.value)


def _mismatched_suppression():
    text = TextPlacement("label", "obj", "hidden", BOUNDS, "text", overflow="suppressed",
                         required=False, semantic_id="memberLabel", lane_row_id="lane",
                         lane_member_id="actual-member")
    fact = LaneLabelSuppression("label", "lane", "wrong-member", BOUNDS, Decimal(0), "obstruction")
    from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
    SurfacePlacement(text=(text,), diagnostics=("W_LAYOUT_LABEL_SUPPRESSED:label",),
                     rows=(RowPlacement("lane", "obj", "", BOUNDS),),
                     lane_label_suppressions=(fact,),
                     info_diagnostics=(SuppressedPlotLabels("surface", 1),)).assert_valid()


@pytest.mark.parametrize("make,code,operand", [
    (lambda: RowPlacement("row-77", "obj", "", BOUNDS, lane_mark_band_block=Decimal(41)),
     "E_LAYOUT_LANE_ROW_ANCHOR_INVALID", "anchor=41"),
    (lambda: PlacementDecision("decision-77", "obj", (), None, "placed", search_count=-77),
     "E_LAYOUT_PLACEMENT_DECISION_INVALID", "search_count=-77"),
    (lambda: FitWarning("W_LAYOUT_FIT", "fit-77", "obj", "fit", "overflow", -77, 1, 1, 1),
     "E_LAYOUT_FIT_WARNING_INVALID", "required=-77x1"),
    (lambda: LaneEmissionFacet("facet-77", "mark", "mark", "primitive", ObstacleRect(0, 0, 1, 1),
                               "mark", part_index=-77), "E_LAYOUT_LANE_EMISSION_INVALID", "part_index=-77"),
    (lambda: LaneEmissionPlacement("mark", "placement-77", "row", "member", "planned", ()),
     "E_LAYOUT_LANE_EMISSION_INVALID", "placement-77"),
    (lambda: LaneEmissionPlacement("mark", "placement-77", "row", "member", "planned", None),
     "E_LAYOUT_LANE_EMISSION_INVALID", "facets_type=NoneType"),
    (lambda: CapacitySourceEvidence("timeline", Decimal(77), Decimal(88)),
     "E_LAYOUT_SUPPRESSION_EVIDENCE_INVALID", "allocated_block=88"),
    (lambda: LaneLabelSuppression("label-77", "lane", "member", BOUNDS, Decimal(-77), "obstruction"),
     "E_LAYOUT_SUPPRESSION_EVIDENCE_INVALID", "remaining_capacity=-77"),
    (_mismatched_suppression, "E_LAYOUT_SUPPRESSION_EVIDENCE_INVALID", "wrong-member"),
    (lambda: SurfacePlacement(diagnostics=(), lane_label_suppressions=(
        LaneLabelSuppression("label", "lane", "member", BOUNDS, Decimal(0), "obstruction"),
    )).assert_valid(), "E_LAYOUT_SUPPRESSION_COUNT_INVALID", "evidence=1"),
    (lambda: SurfacePlacement(canvas_bounds=Rect(Decimal(0), Decimal(0), Decimal(-77), Decimal(2))).assert_valid(),
     "E_LAYOUT_CANVAS_BOUNDS_INVALID", "inline_size=-77"),
    (lambda: SurfacePlacement(patterns=(SimpleNamespace(placement_id="duplicate-77"),
                                       SimpleNamespace(placement_id="duplicate-77"))).assert_valid(),
     "E_LAYOUT_PATTERN_PLACEMENT_DUPLICATE", "duplicate-77"),
])
def test_placement_invariant_names_actual_owner_or_measurement(make, code, operand):
    with pytest.raises(ValueError) as raised:
        make()
    assert str(raised.value).startswith(code + ":")
    assert operand in str(raised.value)
