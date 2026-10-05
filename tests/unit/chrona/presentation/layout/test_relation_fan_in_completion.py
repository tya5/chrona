from dataclasses import replace

import pytest

from chrona.presentation.layout.relation_fan_in import (
    NodeApproach, complete_fan_in, same_port_arrivals, target_port_identity, terminal_style,
)
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_quality import RelationFanIn, RelationPlacement


def _head(shape="triangle"):
    return marker_geometry({"shape": shape, "headLength": 6, "headWidth": 6, "attachmentOffset": 0})


@pytest.mark.parametrize("field", ("target_port_id", "terminal_owner_id"))
@pytest.mark.parametrize("invalid", ("", None, 123))
def test_invalid_fan_in_identity_names_the_field_and_required_value(field, invalid):
    values = {"target_port_id": "target:start", "terminal_owner_id": "relation:one"}
    values[field] = invalid
    with pytest.raises(ValueError) as error:
        RelationFanIn(**values)
    assert str(error.value) == f"E_PRESENTATION_PRIMITIVE_INVALID: fan_in.{field} must be a non-empty string"


def _route(name, *, node="target", port="target:start", marker=None):
    return RelationPlacement(name, f"{name}:end", port, ((0, 0), (0, 10), (20, 10)),
        from_instance_id=name, to_instance_id=node, marker_end=marker)


def test_semantic_port_identity_normalizes_finish_without_aliasing_point_ports():
    assert target_port_identity("t", "finish", "above", point=False) == target_port_identity(
        "t", "end", "end", point=False)
    assert target_port_identity("t", "at", "above", point=True) != target_port_identity(
        "t", "at", "below", point=True)
    assert target_port_identity("t", "start", "start", point=True) == target_port_identity(
        "t", "at", "start", point=True)


def test_shared_arrivals_preserve_all_routes_and_first_declared_head_owner():
    original = tuple(_route(name, marker=_head()) for name in ("second", "first", "third"))
    result = complete_fan_in(original)
    assert tuple(item.relation_id for item in result) == ("second", "first", "third")
    assert tuple(item.points for item in result) == tuple(item.points for item in original)
    assert [item.marker_end is not None for item in result] == [True, False, False]
    assert all(item.fan_in.terminal_owner_id == "second" for item in result)
    assert all(item.fan_in.target_port_id == "target:start" for item in result)


@pytest.mark.parametrize("mutation", [
    {"target_port_id": "target:end"}, {"to_instance_id": "other"},
    {"semantic_id": "other-paint"}, {"marker_end": _head("chevron")},
    {"points": ((30, 0), (30, 10), (20, 10))},
])
def test_different_ports_instances_paints_heads_and_directions_never_share(mutation):
    first = _route("one", marker=_head())
    second = replace(_route("two", marker=_head()), **mutation)
    assert all(item.fan_in is None for item in complete_fan_in((first, second)))


def test_arrival_departure_overlap_is_not_authorized_by_a_port_match():
    arrival = NodeApproach("one", ((0, 0), (20, 0)), "target:start", "dependency")
    departure = NodeApproach("two", ((0, 0), (20, 0)))
    assert not same_port_arrivals(arrival, departure)
    assert not same_port_arrivals(departure, arrival)


def test_headless_group_stays_headless():
    result = complete_fan_in((_route("one"), _route("two")))
    assert all(item.fan_in is not None and item.marker_end is None for item in result)


def test_centered_heads_group_by_semantic_port_not_painted_setback():
    circle = _head("circle")
    first = _route("one", marker=circle)
    second = replace(_route("two"), marker_end=replace(circle, attachment_offset=2),
                     points=((0, 0), (0, 10), (19, 10)))
    assert terminal_style(first.marker_end) == terminal_style(second.marker_end)
    result = complete_fan_in((first, second))
    assert result[0].marker_end is circle and result[1].marker_end is None
    assert result[0].points == first.points and result[1].points == second.points
