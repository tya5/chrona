"""Selected-fact workload estimates that do not depend on completed geometry."""
from __future__ import annotations

from collections import Counter
from itertools import chain

from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.model.surface_content import SurfaceContentInput


ROUTING_COST_ADVISORY_THRESHOLD = 336


def routing_cost_advisory(
    projection: ReviewProjection, content: SurfaceContentInput,
) -> RoutingCostAdvisory | None:
    """Estimate possible endpoint pairs from selected occurrences and relation facts.

    This deliberately runs before route placement and count-closure trials. The
    estimate is conservative: each selected relation can expand across every
    selected occurrence of its source and target objects.
    """
    if projection.surface != "table-timeline":
        return None
    ordinary = ((item for row in projection.rows for item in row.items)
                if projection.has_rows else iter(projection.items))
    folded = (item for point in projection.folded_points for item in point.all_items)
    multiplicities = Counter(item.object_id for item in chain(ordinary, folded))
    if not multiplicities:
        return None

    potential_pairs = sum(
        multiplicities.get(relation.source_object_id, 0)
        * multiplicities.get(relation.target_object_id, 0)
        for relation in content.relations
    )
    if potential_pairs < ROUTING_COST_ADVISORY_THRESHOLD:
        return None
    return RoutingCostAdvisory("table-timeline", potential_pairs)
