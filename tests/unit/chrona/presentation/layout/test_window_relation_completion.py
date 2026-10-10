"""Window omission precedes routing and cannot fall back to a row anchor."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.surface_routes import SurfaceRoutesContext, compose_surface_routes
from chrona.presentation.layout.surface_mark_visibility import build_item_mark_visibility_index
from chrona.presentation.layout.surface_quality import SurfacePlacement
from chrona.presentation.model.surface_content import RelationPresentationFact
from chrona.presentation.model.projection import FoldedPointProjection, WindowMode
from tests.unit.chrona.presentation.layout.test_lane_item_footprints import _window_footprint_fixture
from tests.unit.chrona.presentation.layout.test_window_lane_completion import _request


@pytest.mark.parametrize("source,target", [("object-1", "object-4"), ("object-4", "object-6"),
                                          ("object-1", "object-6")])
@pytest.mark.parametrize("overflow", ["suppress", "visible-overflow"])
def test_omitted_original_endpoint_suppresses_before_route_search_or_fallback(monkeypatch, source, target, overflow):
    request = _request()
    fact = RelationPresentationFact("dep", source, "end", target, "start", 0, None, "dependency")
    request = replace(request, surface_content=replace(request.surface_content,
        relations=(fact,), relation_overflow=overflow))
    monkeypatch.setattr("chrona.presentation.layout.surface_routes.select_relation_route",
                        lambda *a, **k: pytest.fail("omitted endpoints must not enter route search"))
    placement = compose_surface_layout(request).placement
    assert len(placement.relations) == 1
    relation = placement.relations[0]
    assert relation.suppressed and relation.points == relation.path_commands == ()
    assert relation.source_ref == "dep" and relation.semantic_id == "dependency"
    expected = {value for value in (source, target) if value != "object-4"}
    assert {proof.occurrence.object_id for proof in relation.window_endpoint_absences} == expected
    assert all(proof.reason == "outside-window" and proof.source_ref for proof in relation.window_endpoint_absences)
    assert placement.diagnostics.count(f"W_LAYOUT_RELATION_SUPPRESSED:{relation.relation_id}") == 1
    placement.assert_valid()


def test_containing_window_keeps_real_relation_completion_identical_to_derived():
    fact = RelationPresentationFact("dep", "object-1", "end", "object-4", "start", 0, None, "dependency")
    def compose(mode):
        request = _request(containing=True, mode=mode)
        return compose_surface_layout(replace(request, surface_content=replace(
            request.surface_content, relations=(fact,)))).placement
    explicit, derived = compose(WindowMode.EXPLICIT), compose(WindowMode.SELECTED_PLANNED)
    assert explicit == derived
    assert len(explicit.relations) == 1
    assert explicit.relations[0].window_endpoint_absences == ()


def test_two_cut_original_ports_never_route_from_the_visible_host_edges(monkeypatch):
    projection, _, _ = _window_footprint_fixture()
    original = projection.items[1]
    across = replace(original, planned={"start": date(2026, 1, 1), "end": date(2026, 1, 9)})
    items = (projection.items[0], across, projection.items[2])
    projection = replace(projection, items=items,
        rows=tuple(replace(row, items=(item,)) for row, item in zip(projection.rows, items, strict=True)),
        lane_rows=(replace(projection.lane_rows[0], items=items),))
    request = _request(projection=projection)
    fact = RelationPresentationFact("dep", "object-4", "start", "object-4", "end", 0, None, "dependency")
    monkeypatch.setattr("chrona.presentation.layout.surface_routes.select_relation_route",
                        lambda *a, **k: pytest.fail("cut edges cannot substitute original ports"))
    placement = compose_surface_layout(replace(request, surface_content=replace(
        request.surface_content, relations=(fact,)))).placement
    assert len(placement.marks) == 1
    assert placement.marks[0].start_port is placement.marks[0].end_port is None
    relation = placement.relations[0]
    assert relation.suppressed
    assert {proof.endpoint for proof in relation.window_endpoint_absences} == {"start", "end"}


def test_omitted_folded_gates_retain_relation_identity_without_generic_anchor(monkeypatch):
    projection, _, _ = _window_footprint_fixture(point=True, all_outside=True)
    projection = replace(projection, items=(), rows=(), lane_membership=None, lane_rows=(),
        folded_points=tuple(FoldedPointProjection(item, "group") for item in projection.items))
    index = build_item_mark_visibility_index(projection, as_of=None)
    request = _request()
    fact = RelationPresentationFact("dep", "object-1", "at", "object-6", "at", 0, None, "dependency")
    request = replace(request, projection=projection, mark_visibility_index=index,
                      surface_content=replace(request.surface_content, relations=(fact,)))
    monkeypatch.setattr("chrona.presentation.layout.surface_routes.select_relation_route",
                        lambda *a, **k: pytest.fail("omitted folded gates have no route geometry"))
    result = compose_surface_routes(SurfaceRoutesContext(request, projection, (), (), (), (),
        (0, 0, 100, 100), request.layout_manifest, {}, (), SurfaceObstacleIndex()))
    assert result.instance_anchors == {}
    assert len(result.relations) == 1 and result.relations[0].suppressed
    assert {proof.occurrence.object_id for proof in result.relations[0].window_endpoint_absences} == {
        "object-1", "object-6"}


@pytest.mark.parametrize("change", [{"suppressed": False, "points": ((0, 0), (1, 0))},
                                    {"source_ref": ""}, {"window_endpoint_absences": ({},)}])
def test_completed_relation_rejects_unowned_or_painted_window_absence(change):
    request = _request()
    fact = RelationPresentationFact("dep", "object-1", "end", "object-4", "start", 0, None, "dependency")
    placement = compose_surface_layout(replace(request, surface_content=replace(
        request.surface_content, relations=(fact,)))).placement
    invalid = replace(placement.relations[0], **change)
    with pytest.raises(ValueError, match="E_LAYOUT_RELATION_SUPPRESSION_INVALID"):
        SurfacePlacement(relations=(invalid,)).assert_valid()
