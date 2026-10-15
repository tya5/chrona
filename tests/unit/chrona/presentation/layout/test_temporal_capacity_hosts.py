"""The selected refusal rule does not infer growth from host ancestry."""
from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.temporal_capacity import TemporalInlineCapacity


@pytest.mark.parametrize("bounded", [False, True])
def test_table_floor_leaves_zero_timeline_in_bounded_and_unbounded_hosts(bounded):
    def slot(source, inline):
        return {"id": source + "-host", "kind": "slot", "source": source,
                "inlineSize": inline, "blockSize": "fill", "priority": "required",
                "place": {"inline": "stretch", "block": "stretch", "safety": "strict"},
                "overflow": "visible-overflow"}

    profile = resolve_layout_profile({
        "version": "chrona/layout-profile/v0.10", "id": "temporal-host",
        "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal",
        "requiredThemeTokens": ["spacing.none"],
        "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {
            "rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both",
            "calendarClosed": "timeline"}, "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
        "root": {"id": "host", "kind": "row", "blockSize": "fill",
                 "inlineSize": {"minmax": {"min": {"fixed": 0}, "max": {"fixed": 100}}}
                 if bounded else "fill",
                 "padding": {"token": "spacing.none"}, "gap": {"token": "spacing.none"},
                 "alignItems": "stretch", "justifyContent": "start",
                 "children": [slot("table", {"fixed": 100}), slot("timeline", {"fr": 1})]},
    }, available_sources={"table", "timeline"}, theme={"body": {"values": {
        "spacing.none": {"type": "number", "value": 0}}}})
    measurements = {source: Measurement(Decimal(0), Decimal(120), Decimal(240),
                                       Decimal(0), Decimal(40), Decimal(80))
                    for source in ("table", "timeline")}
    manifest = solve_layout(profile, viewport_inline=100, viewport_block=40,
                            measurements={source + "-host": value for source, value in measurements.items()})
    capacity = TemporalInlineCapacity.from_manifest(manifest, MeasuredSources(measurements, {}, {}))
    assert capacity.allocated_inline == 0
    assert capacity.natural_inline == 120
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_INLINE_CAPACITY") as error:
        capacity.require_usable(3, 5)
    assert error.value.node_id == "timeline-host"
    assert "required_inline=128" in error.value.detail
