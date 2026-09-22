from chrona.presentation.layout.routing import place_relation_route, relation_route_quality


def test_place_relation_route_returns_completed_orthogonal_points():
    points = place_relation_route(source_port=(1, 1), target_port=(9, 9), obstacles=(), bounds=(0, 0, 10, 10))
    assert points[0] == (1, 1) and points[-1] == (9, 9)


def test_relation_quality_applies_declared_bend_and_detour_limits():
    route = ((1, 1), (1, 9), (9, 9))
    assert relation_route_quality(route, max_bends=1, max_detour_ratio=1.0)
    assert not relation_route_quality(route, max_bends=0, max_detour_ratio=2.0)
