from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.network_legend import complete_network_legend, prepare_network_legend
from chrona.presentation.layout.sources import resolve_theme_metrics
from chrona.presentation.layout.surface_quality import RelationPlacement, SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_sources import theme as measuring_theme


@dataclass(frozen=True)
class _Content:
    legend_entries: tuple[SurfaceLegendEntry, ...]


class _Metrics:
    content_identity = "sha256:network-legend-test"

    def width(self, value, size):
        return len(value) * size / 2

    def baseline(self, top, size, line_height):
        return top + size


def _theme():
    value = measuring_theme()
    value["body"]["values"].update({
        "critical-edge-width": {"type": "number", "value": 2},
        "critical-edge-ink": {"type": "color", "value": "#B91C1C"},
        "dependency-width": {"type": "number", "value": 1},
        "dependency-ink": {"type": "color", "value": "#334155"},
    })
    value["body"]["roles"].update({
        "critical-edge": {"stroke": "critical-edge-ink", "strokeWidth": "critical-edge-width"},
        "dependency": {"stroke": "dependency-ink", "strokeWidth": "dependency-width"},
    })
    return value


def _request(entries, *, edge=True, manifest_ids=()):
    theme = _theme()
    edge_value = SimpleNamespace(relation_id="edge", critical=True, source_id="a", target_id="b")
    network = SimpleNamespace(edges=(edge_value,) if edge else (),
                              nodes=(SimpleNamespace(object_id="a"), SimpleNamespace(object_id="b")))
    metrics = _Metrics()
    return SurfaceLayoutRequest(
        projection=SimpleNamespace(network=network),
        surface_content=_Content(tuple(entries)),
        layout_manifest=SimpleNamespace(decisions=tuple(SimpleNamespace(node_id=item) for item in manifest_ids)),
        measured_sources=SimpleNamespace(metric_values=resolve_theme_metrics(theme), legend_layout=None),
        theme_tokens=ThemeTokenView(theme), font_metrics=metrics,
    )


def _relation(*, critical=True, suppressed=False, points=((10.0, 10.0), (20.0, 10.0))):
    return RelationPlacement("edge", "a:output", "b:input", points,
                             suppressed=suppressed,
                             semantic_id="criticalEdge" if critical else "networkEdge")


def test_intrinsic_legend_filters_to_critical_key_and_reserves_measured_band():
    request = _request((SurfaceLegendEntry("critical-edge", "Critical dependency"),
                        SurfaceLegendEntry("dependency", "Other dependencies")),
                       manifest_ids=("network-intrinsic-legend",))
    network_slot = SlotPlacement("network-slot", "network", Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(100)))

    plan = prepare_network_legend(request, network_slot, None, heading_block=Decimal(12))

    assert plan.intrinsic
    assert plan.heading_block == Decimal(0)
    assert tuple(entry.role for entry in plan.request.surface_content.legend_entries) == ("critical-edge",)
    assert plan.graph_slot.bounds.block_size < network_slot.bounds.block_size
    assert plan.legend_slot is not None and plan.legend_slot.source_ref == "legend"
    assert plan.legend_slot.slot_id == "network-intrinsic-legend-2"
    assert plan.legend_slot.bounds.block == (
        plan.graph_slot.bounds.block + plan.graph_slot.bounds.block_size + plan.block_gap)

    batch = complete_network_legend(plan, (_relation(),), ())

    assert batch is not None
    assert tuple(relation.semantic_id for relation in batch.relations) == ("criticalEdge",)
    assert tuple(relation.source_ref for relation in batch.relations) == ("critical-edge",)


def test_intrinsic_band_moves_below_actual_graph_overflow_and_requires_drawn_edge():
    request = _request((SurfaceLegendEntry("critical-edge", "Critical dependency"),))
    network_slot = SlotPlacement("network-slot", "network", Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(100)))
    plan = prepare_network_legend(request, network_slot, None)
    assert plan.legend_slot is not None
    graph_bottom = plan.legend_slot.bounds.block + plan.legend_slot.bounds.block_size

    batch = complete_network_legend(
        plan, (_relation(),), (Rect(Decimal(0), plan.legend_slot.bounds.block - Decimal(5),
                                    Decimal(100), Decimal(30)),))
    assert batch is not None
    assert batch.slot.bounds.block == plan.legend_slot.bounds.block + Decimal(25) + plan.block_gap
    assert batch.slot.bounds.block > graph_bottom

    assert complete_network_legend(plan, (_relation(suppressed=True),), ()) is None
    assert complete_network_legend(plan, (_relation(points=((4.0, 4.0), (4.0, 4.0))),), ()) is None


def test_authored_legend_keeps_all_keys_and_layout_settings_when_moved():
    entries = (SurfaceLegendEntry("critical-edge", "Critical dependency"),
               SurfaceLegendEntry("dependency", "Other dependencies"))
    request = _request(entries)
    network_slot = SlotPlacement("network-slot", "network", Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(100)))
    authored_slot = SlotPlacement("authored-legend", "legend",
                                  Rect(Decimal(50), Decimal(10), Decimal(160), Decimal(36)),
                                  direction="inline", gap=Decimal(4), columns=2)
    plan = prepare_network_legend(request, network_slot, authored_slot)

    assert not plan.intrinsic and plan.graph_slot == network_slot and plan.legend_slot == authored_slot
    assert tuple(entry.role for entry in plan.request.surface_content.legend_entries) == (
        "critical-edge", "dependency")
    unchanged = complete_network_legend(plan, (_relation(),),
                                        (Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(8)),))
    assert unchanged is not None and unchanged.slot.direction == "inline"
    assert len(unchanged.relations) == 2

    moved = complete_network_legend(plan, (_relation(),),
                                    (Rect(Decimal(50), Decimal(30), Decimal(100), Decimal(20)),))
    assert moved is not None
    assert moved.slot.direction == "inline"
    assert moved.slot.gap == Decimal(4) and moved.slot.columns == 2
    assert moved.slot.bounds.block == Decimal(50) + plan.block_gap
    assert moved.slot.bounds.inline == authored_slot.bounds.inline
    # Completion grows the authored minimum to the measured full-key extent;
    # relocation must preserve that same completed width, not the pre-closure slot width.
    assert moved.slot.bounds.inline_size == unchanged.slot.bounds.inline_size
    assert moved.slot.bounds.inline_size >= authored_slot.bounds.inline_size
    assert {item.content for item in moved.text} == {"Critical dependency", "Other dependencies"}
    assert len(moved.relations) == 2


def test_authored_legend_collision_includes_reserved_caption_band():
    entries = (SurfaceLegendEntry("dependency", "Other dependencies"),)
    request = _request(entries)
    network_slot = SlotPlacement("network-slot", "network", Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(100)))
    authored_slot = SlotPlacement("authored-legend", "legend",
                                  Rect(Decimal(50), Decimal(20), Decimal(160), Decimal(36)),
                                  direction="inline")
    heading = Decimal(12)
    plan = prepare_network_legend(request, network_slot, authored_slot, heading_block=heading)

    # This rect intersects only the reserved caption, not the content slot.
    occupied = Rect(Decimal(50), Decimal(9), Decimal(100), Decimal(4))
    batch = complete_network_legend(plan, (_relation(critical=False),), (occupied,))

    assert batch is not None
    restored_heading_top = batch.slot.bounds.block - heading
    assert restored_heading_top == occupied.block + occupied.block_size + plan.block_gap
    assert batch.slot.bounds.inline == authored_slot.bounds.inline
    assert batch.slot.direction == authored_slot.direction


def test_overflow_flow_clears_later_graph_rows_not_just_the_initial_collision():
    request = _request((SurfaceLegendEntry("critical-edge", "Critical dependency"),))
    slot = SlotPlacement("network", "network", Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(100)))
    plan = prepare_network_legend(request, slot, None)
    top = plan.legend_slot.bounds.block
    occupied = (Rect(Decimal(0), top - 1, Decimal(20), Decimal(10)),
                Rect(Decimal(0), top + 20, Decimal(20), Decimal(20)))

    batch = complete_network_legend(plan, (_relation(),), occupied)

    assert batch.slot.bounds.block == top + 40 + plan.block_gap
    assert all(item.semantic_id == "legendLabel" and item.slot_id == batch.slot.slot_id
               for item in batch.text)
    assert all(item.paint_bounds is not None for item in batch.relations)


def test_no_candidate_has_no_intrinsic_slot_and_suppression_drops_only_intrinsic_key():
    network_slot = SlotPlacement("network-slot", "network", Rect(Decimal(0), Decimal(0), Decimal(240), Decimal(100)))
    no_candidate = prepare_network_legend(
        _request((SurfaceLegendEntry("dependency", "Other dependencies"),), edge=False),
        network_slot, None)
    assert no_candidate.legend_slot is None and no_candidate.graph_slot == network_slot
    assert complete_network_legend(no_candidate, (), ()) is None

    authored = prepare_network_legend(
        _request((SurfaceLegendEntry("critical-edge", "Critical dependency"),
                 SurfaceLegendEntry("dependency", "Other dependencies"))),
        network_slot,
        SlotPlacement("authored-legend", "legend", Rect(Decimal(0), Decimal(10), Decimal(240), Decimal(40))))
    batch = complete_network_legend(authored, (_relation(suppressed=True),), ())
    assert batch is not None
    assert tuple(relation.source_ref for relation in batch.relations) == ("dependency",)
