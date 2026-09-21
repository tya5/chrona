from chrona.presentation.layout.routing import place_relation_route


def test_place_relation_route_returns_completed_orthogonal_points():
    points = place_relation_route(source_port=(1, 1), target_port=(9, 9), obstacles=(), bounds=(0, 0, 10, 10))
    assert points[0] == (1, 1) and points[-1] == (9, 9)
