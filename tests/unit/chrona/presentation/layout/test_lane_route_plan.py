"""Member names are completed once by their Layout owner before route search."""
from chrona.presentation.layout.labels import CollisionDomain, LabelRect, LabelRequest
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.surface_member_labels import place_member_labels
from tests.unit.chrona.presentation.layout.test_member_label_required_phase import _placement_context


def test_member_name_owner_places_one_candidate_without_corridor_reservation():
    request = LabelRequest("member-label:a", "a", "Owner", LabelRect(80, 40, 10, 10),
        ("end", "start"), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "suppress", semantic_id="memberLabel")
    obstacles = SurfaceObstacleIndex()

    batch = place_member_labels(_placement_context(), (request,), obstacles)

    assert len(batch.text) == 1
    assert batch.text[0].placement_id == request.placement_id
    assert [item.decision_id for item in batch.decisions] == [request.placement_id]
    assert not any(item.obstacle_class == "route-reserve" for item in obstacles.all())
