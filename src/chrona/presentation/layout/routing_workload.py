"""Advisory policy over a prepared normal-domain connector workload."""
from __future__ import annotations

from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory


# Conservative normal-domain lower bound from the measured trial9 target-b
# sample (2865 pairs minus at most 33 recovery selections of 15 pairs).
ROUTING_COST_ADVISORY_THRESHOLD = 2370


def routing_cost_advisory(surface_id: str, potential_port_pairs: int) -> RoutingCostAdvisory | None:
    """Observe potential pair domains, never evaluated searches or elapsed time.

    Layout supplies the total from the same ordered normal-stage preparation
    that routing consumes. Recovery stages are contingent and are not counted.
    """
    if (isinstance(potential_port_pairs, bool) or not isinstance(potential_port_pairs, int)
            or potential_port_pairs < 0):
        raise ValueError("potential_port_pairs must be a nonnegative integer")
    if surface_id != "table-timeline" or potential_port_pairs < ROUTING_COST_ADVISORY_THRESHOLD:
        return None
    return RoutingCostAdvisory(surface_id, potential_port_pairs)
