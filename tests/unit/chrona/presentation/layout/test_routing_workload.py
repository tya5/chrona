from types import SimpleNamespace
from datetime import date

from chrona.presentation.layout.routing_workload import ROUTING_COST_ADVISORY_THRESHOLD, routing_cost_advisory
from chrona.presentation.model.projection import ReviewProjection


def _occurrence(object_id):
    return SimpleNamespace(object_id=object_id)


def _relation(source, target):
    return SimpleNamespace(source_object_id=source, target_object_id=target)


def _projection(*, rows=(), items=(), folded_points=(), rows_resolved=True, surface="table-timeline"):
    return ReviewProjection(items=tuple(items), window=(date.min, date.max), unmatched_actual_ids=(),
                            diagnostics=(), rows=tuple(rows), folded_points=tuple(folded_points),
                            rows_resolved=rows_resolved, surface=surface)


def _row(*items):
    return SimpleNamespace(items=tuple(items))


def _folded(*items):
    return SimpleNamespace(all_items=tuple(items))


def _content(*relations):
    return SimpleNamespace(relations=tuple(relations))


def test_routing_cost_advisory_threshold_is_inclusive_and_counts_relation_products():
    source = _occurrence("source")
    targets = tuple(_occurrence("target") for _ in range(ROUTING_COST_ADVISORY_THRESHOLD - 1))
    projection = _projection(rows=(_row(source, *targets),))
    content = _content(_relation("source", "target"))

    assert routing_cost_advisory(projection, content) is None

    projection = _projection(rows=(_row(source, *targets, _occurrence("target")),))
    advisory = routing_cost_advisory(projection, content)
    assert (advisory.surface_id, advisory.potential_pairs) == ("table-timeline", 336)


def test_routing_cost_advisory_includes_duplicate_and_folded_occurrences_per_relation():
    ordinary = (_row(_occurrence("source"), _occurrence("source")),
                _row(*(_occurrence("target") for _ in range(110))))
    folded = (_folded(_occurrence("source")),
              _folded(_occurrence("target"), _occurrence("target")))
    projection = _projection(rows=ordinary, folded_points=folded)
    # Three source occurrences × 112 target occurrences; a selected duplicate
    # relation is a second fact and contributes its own product.
    advisory = routing_cost_advisory(
        projection, _content(_relation("source", "target"), _relation("source", "target")))

    assert advisory.potential_pairs == 672


def test_routing_cost_advisory_uses_legacy_items_fallback_and_skips_missing_endpoints():
    projection = _projection(rows=(), rows_resolved=False,
                             items=(_occurrence("source"), *(_occurrence("target")
                                                              for _ in range(ROUTING_COST_ADVISORY_THRESHOLD))))
    content = _content(_relation("source", "target"), _relation("missing", "target"))

    advisory = routing_cost_advisory(projection, content)
    assert advisory.potential_pairs == 336

    assert routing_cost_advisory(
        _projection(rows=(), rows_resolved=True), _content(_relation("missing", "target"))) is None


def test_routing_cost_advisory_is_not_emitted_for_non_timeline_surfaces():
    projection = _projection(rows=(_row(*(_occurrence("source")
                                          for _ in range(ROUTING_COST_ADVISORY_THRESHOLD))),),
                             surface="dependency-network")

    assert routing_cost_advisory(projection, _content(_relation("source", "source"))) is None
