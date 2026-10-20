import pytest

from chrona.presentation.layout.routing_workload import ROUTING_COST_ADVISORY_THRESHOLD, routing_cost_advisory


def test_routing_cost_advisory_threshold_is_inclusive_and_counts_port_domains():
    limit = ROUTING_COST_ADVISORY_THRESHOLD
    assert routing_cost_advisory("table-timeline", limit - 1) is None
    advisory = routing_cost_advisory("table-timeline", limit)
    assert (advisory.surface_id, advisory.potential_port_pairs) == ("table-timeline", 2370)


@pytest.mark.parametrize("count", [0, 1, 9, 234, 336])
def test_small_prepared_domain_counts_do_not_warn(count):
    assert routing_cost_advisory("table-timeline", count) is None


@pytest.mark.parametrize("count", [2370, 2568, 3330])
def test_bounded_measured_expensive_cases_qualify(count):
    assert routing_cost_advisory("table-timeline", count).potential_port_pairs == count


def test_routing_cost_advisory_is_not_emitted_for_non_timeline_surfaces():
    assert routing_cost_advisory("dependency-network", 5000) is None


@pytest.mark.parametrize("count", [-1, True, 1.5])
def test_workload_count_must_be_a_nonnegative_integer(count):
    with pytest.raises(ValueError, match="nonnegative integer"):
        routing_cost_advisory("table-timeline", count)
