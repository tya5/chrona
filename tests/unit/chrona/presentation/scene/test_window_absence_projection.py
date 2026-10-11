"""Scene copies the final Layout owner separately from the source occurrence."""
import pytest

from chrona.presentation.layout.lane_projection import ExpectedLaneMark, LaneProjectionInstance
from chrona.presentation.layout.lane_window_marks import LaneWindowPlacementAbsence
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.scene.model import SceneLaneMember, SceneLaneWindowAbsence
from chrona.presentation.scene.window_absences import project_lane_window_absences
from tests.unit.chrona.presentation.layout.test_window_lane_completion import _request


def _absence(*, facet="planned", role="planned", member="final:member", occurrence="source:occurrence"):
    original = LaneProjectionInstance("source:row", occurrence, "object", "combined")
    mark = ExpectedLaneMark(original, role, facet, "opaque:placement:" + facet)
    return LaneWindowPlacementAbsence("final:row", member, mark, "/source/original")


@pytest.mark.parametrize("facet,role", [("planned", "planned"), ("planned", "snapshot"),
                                       ("planned", "scenario"), ("actual", "actual"),
                                       ("missing-actual", "missing-actual")])
def test_projection_copies_all_source_facts_and_uses_supplied_final_owner(facet, role):
    absence = _absence(facet=facet, role=role)
    projected = project_lane_window_absences((absence,))
    assert tuple(projected) == (("final:row", "final:member"),)
    assert projected[("final:row", "final:member")] == (SceneLaneWindowAbsence(
        "opaque:placement:" + facet, "source%3Arow:source%3Aoccurrence", facet,
        "/source/original", "combined", role, "outside-window"),)


def test_projection_preserves_source_order_within_each_member_without_decoding_ids():
    primary = _absence()
    actual = _absence(facet="actual", role="actual")
    other = _absence(member="another:member", occurrence="other:occurrence")
    projected = project_lane_window_absences((actual, other, primary))
    assert [value.facet for value in projected[("final:row", "final:member")]] == ["actual", "planned"]
    assert tuple(projected) == (("final:row", "final:member"), ("final:row", "another:member"))
    assert all(value.instance_id != owner[1] for owner, values in projected.items() for value in values)


def test_no_omission_metadata_is_added_to_a_containing_window():
    placement = compose_surface_layout(_request(containing=True)).placement
    assert project_lane_window_absences(placement.lane_window_absences) == {}


@pytest.mark.parametrize("point", [False, True])
def test_real_fully_omitted_layout_projects_empty_member_without_fake_geometry(point):
    placement = compose_surface_layout(_request(point=point, all_outside=True)).placement
    assert placement.marks == placement.lane_emissions == ()
    projected = project_lane_window_absences(placement.lane_window_absences)
    assert {owner[1] for owner in projected} == {"item-1", "item-6"}
    for owner, values in projected.items():
        member = SceneLaneMember(*owner, (), (), values)
        assert member.emitted_primitive_ids == member.primary_mark_ids == ()
        assert member.window_absences == values


def test_real_mixed_layout_keeps_only_original_omissions_in_metadata():
    placement = compose_surface_layout(_request()).placement
    projected = project_lane_window_absences(placement.lane_window_absences)
    assert {owner[1] for owner in projected} == {"item-1", "item-6"}
    assert {mark.source_ref for mark in placement.marks} == {"object-4"}
    assert all(value.source_ref != "object-4" for values in projected.values() for value in values)


def test_projection_does_not_turn_an_actual_absence_into_primary_omission_proof():
    absence = _absence(facet="actual", role="actual")
    values = project_lane_window_absences((absence,))[(absence.row_id, absence.member_id)]
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneMember(absence.row_id, absence.member_id, (), (), values)
