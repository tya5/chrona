"""Finite overlap geometry retains endpoint corridors and never invokes search."""
from dataclasses import replace

import pytest

from chrona.presentation.layout.ports import (
    ConnectorEgress, outward_corridor_ends, split_route_at_physical_corridors,
)
from chrona.presentation.layout.relation_fallback import (
    complete_fixed_connector, fixed_connector_candidates, paired_stub_geometry,
)
from chrona.presentation.layout.routing import route_self_overlaps
from chrona.presentation.layout.surface_quality import RelationPlacement


PAIR = (ConnectorEgress("end", (0., 0.), (0., 0.), ("source",)),
        ConnectorEgress("start", (100., 20.), (100., 20.), ("target",)))


def test_finite_orthogonal_candidates_preserve_semantic_endpoints_and_outward_corridors():
    paths = fixed_connector_candidates(PAIR, source_run=6., target_run=9.)
    assert 1 <= len(paths) <= 6 and len(set(paths)) == len(paths)
    for path in paths:
        assert path[0] == PAIR[0].semantic_port and path[-1] == PAIR[1].semantic_port
        assert path[1] == (6., 0.) and path[-2] == (91., 20.)
        assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(path, path[1:]))


def test_shared_outward_leads_keep_endpoint_corridors_and_match_fixed_fallback():
    pair = (replace(PAIR[0], exposed_port=(4., 0.)),
            replace(PAIR[1], exposed_port=(95., 20.)))
    leads = outward_corridor_ends(pair, source_run=16., target_run=12.)
    assert leads == ((20., 0.), (83., 20.))
    paths = fixed_connector_candidates(pair, source_run=16., target_run=12.)
    assert paths[0] == ((0., 0.), (4., 0.), (20., 0.), (83., 0.), (83., 20.), (95., 20.), (100., 20.))


def test_preparation_rejection_tries_next_fixed_candidate_without_graph_search():
    tried = []
    def prepare(path, source, target):
        tried.append(path)
        return None if len(tried) == 1 else path
    result = complete_fixed_connector((PAIR,), lead_runs=lambda _source, _target: (6., 9.),
        prepare=prepare, accept=lambda points: not route_self_overlaps(points))
    assert result is not None and result.points == tried[-1] and len(tried) == 2


def test_uncompletable_host_egress_returns_none_for_paired_stub_completion():
    calls = []
    def reject(path, source, target):
        calls.append(path)
        return None
    assert complete_fixed_connector((PAIR,), lead_runs=lambda _source, _target: (6., 9.),
        prepare=reject, accept=lambda points: True) is None
    assert 1 <= len(calls) <= 6


def test_fixed_recovery_uses_shared_residual_leads_not_a_second_full_terminal_reserve():
    from chrona.presentation.layout.relation_endpoint_geometry import endpoint_lead_run
    from chrona.presentation.layout.relation_terminals import marker_geometry

    marker = marker_geometry({"shape": "circle", "headLength": 5, "headWidth": 5})
    pair = (replace(PAIR[0], exposed_port=(4., 0.)), PAIR[1])
    observed = []
    def leads(source, target):
        result = (endpoint_lead_run(source.exposed_port, source.semantic_port, 1, marker),
                  endpoint_lead_run(target.exposed_port, target.semantic_port, 1, marker))
        observed.append(result)
        return result

    completed = complete_fixed_connector((pair,), lead_runs=leads,
        prepare=lambda path, _source, _target: path, accept=lambda _path: True)

    assert observed == [(0., 3.5)]
    assert completed is not None
    assert completed.points[1] == (4., 0.)  # the completed host corridor already exceeds 3.5
    assert completed.points[-2] == (96.5, 20.)


@pytest.mark.parametrize("run", (-1., float("nan"), float("inf"), True, "1"))
def test_invalid_corridor_metrics_are_not_painted(run):
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        fixed_connector_candidates(PAIR, source_run=run, target_run=9.)


def test_nonfinite_port_is_rejected():
    pair = (replace(PAIR[0], exposed_port=(float("nan"), 0.)), PAIR[1])
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        fixed_connector_candidates(pair, source_run=6., target_run=9.)


def test_paired_stubs_retain_two_independent_semantic_endpoints():
    paired = paired_stub_geometry(PAIR, source_run=16., target_run=12.)
    assert paired.source == ((0., 0.), (16., 0.))
    assert paired.target == ((88., 20.), (100., 20.))
    assert paired.source[-1] != paired.target[0]


def test_paired_stubs_retain_exposed_comparison_corridors():
    pair = (replace(PAIR[0], exposed_port=(4., 0.), corridor_host_ids=("source-host",)),
            replace(PAIR[1], exposed_port=(95., 20.), corridor_host_ids=("target-host",)))
    paired = paired_stub_geometry(pair, source_run=16., target_run=12.)
    assert paired.source == ((0., 0.), (20., 0.))
    assert paired.target == ((83., 20.), (100., 20.))
    assert split_route_at_physical_corridors(paired.source, pair[0], None) == (
        ((0., 0.), (4., 0.), ("source-host",)), ((4., 0.), (20., 0.), ()))
    assert split_route_at_physical_corridors(paired.target, None, pair[1]) == (
        ((83., 20.), (95., 20.), ()), ((95., 20.), (100., 20.), ("target-host",)))


def test_paired_stub_reduces_one_ulp_straight_boundary_without_moving_the_port():
    from math import nextafter

    coordinate = 824.2823529411764
    pair = (replace(PAIR[0], semantic_port=(coordinate, 194.4),
                    exposed_port=(nextafter(coordinate, float("inf")), 194.4)), PAIR[1])
    paired = paired_stub_geometry(pair, source_run=7., target_run=12.)
    assert paired.source == (pair[0].semantic_port, (pair[0].exposed_port[0] + 7., 194.4))
    assert paired.source[0] != pair[0].exposed_port
    assert paired.source[1][0] - paired.source[0][0] >= 7.


def test_paired_stub_keeps_real_short_corner_and_reversal_segments():
    corner = (replace(PAIR[0], side="above", exposed_port=(0.25, 0.)), PAIR[1])
    reversal = (replace(PAIR[0], exposed_port=(-0.25, 0.)), PAIR[1])
    assert paired_stub_geometry(corner, source_run=7., target_run=12.).source == (
        (0., 0.), (0.25, 0.), (0.25, -7.))
    assert paired_stub_geometry(reversal, source_run=7., target_run=12.).source == (
        (0., 0.), (-0.25, 0.), (6.75, 0.))


def test_degenerate_stub_is_not_a_drawn_relation():
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        paired_stub_geometry(PAIR, source_run=0., target_run=12.)


def test_diagonal_or_overflowing_corridor_is_rejected_before_preparation():
    diagonal = (replace(PAIR[0], exposed_port=(1., 1.)), PAIR[1])
    huge = (replace(PAIR[0], exposed_port=(1e308, 0.)), PAIR[1])
    for pair, run in ((diagonal, 6.), (huge, 1e308)):
        with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
            fixed_connector_candidates(pair, source_run=run, target_run=9.)


def test_completed_fragment_requires_owned_endpoint_geometry_and_terminal_text():
    fragment = RelationPlacement("relation:r:stub-source", "source:end", "virtual:out",
        ((0., 0.), (10., 0.)), from_instance_id="source", label_content="-> Target",
        terminal_label=True, fragment_endpoint="source")
    assert fragment.from_instance_id == "source" and fragment.to_instance_id is None
    for changed in ({"to_instance_id": "target"}, {"terminal_label": False},
                    {"label_content": None}, {"points": ()}, {"fragment_endpoint": "unknown"}):
        with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
            replace(fragment, **changed)
