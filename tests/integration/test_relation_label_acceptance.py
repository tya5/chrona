"""Frozen Context evidence for retained relation labels and shared-node routes (#1158)."""
from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
import yaml
import xml.etree.ElementTree as ET

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, segment_overlap_length
from chrona.presentation.layout.ports import connector_egress_candidates, physical_host_neighbors
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.layout.surface_routes import _primary_egress_blockers
from chrona.core.relation_identity import relation_identities
from chrona.presentation.model.closure import resolve_render_context
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.materialize import copy_context_closure
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_controller_baseline_ghosts_retains_label_on_required_shared_comparison_corridor(tmp_path):
    fixture = ROOT / "tests/fixtures/controller-z"
    snapshot = tmp_path / "snapshot"
    reference, _ = copy_context_closure(
        fixture, fixture / "contexts/baseline-ghosts.yaml", snapshot,
    )
    # These authored Contexts are unpinned by design (ADR-0030); their frozen
    # whole-SVG serialization is not the oracle for this geometry regression.
    closure = resolve_render_context(reference, LocalSnapshotReader(
        snapshot, "controller-z-example", require_content_identity=False,
    ))
    rendered = render_review(RenderRequest(closure, snapshot, ReferenceScheduler()))
    svg = ET.fromstring(rendered.artifact.content)
    project = yaml.safe_load((fixture / "project.yaml").read_bytes())
    identities = {relation["id"]: identity
                  for relation, identity in zip(project["relations"], relation_identities(project["relations"]))}
    incoming_id = identities["evb-to-bringup"]
    outgoing_id = identities["bringup-to-performance"]

    label = next(node for node in svg.iter(SVG_NS + "text")
                 if node.attrib.get("data-scene-id", "").startswith(
                     f"relation-label:{outgoing_id}:"))
    assert label.text == "-> Performance Characterization"
    target_label = next(node for node in svg.iter(SVG_NS + "text")
                        if node.attrib.get("data-scene-id", "").startswith(
                            f"relation-label:{outgoing_id}:")
                        and node.attrib.get("data-scene-id", "").endswith(":stub-target"))
    assert target_label.text == "Silicon Bring-up ->"
    resolution, = [item for item in rendered.info_diagnostics
                   if getattr(item, "relation_id", "").startswith(f"relation:{outgoing_id}:")]
    assert resolution.stage.value == "stub"
    assert resolution.fragment_ids and all(fragment in {
        node.attrib.get("data-scene-id") for node in svg.iter()
    } for fragment in resolution.fragment_ids)
    assert not any(item.startswith(f"W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:{outgoing_id}:")
                   for item in rendered.scene.diagnostics)

    primitives = rendered.scene.surfaces[0].primitives
    incoming = next(item for item in primitives
                    if item.scene_id.startswith(f"relation:{incoming_id}:")
                    and item.scene_id.endswith(":stub-target"))
    outgoing = next(item for item in primitives
                    if item.scene_id.startswith(f"relation:{outgoing_id}:")
                    and item.scene_id.endswith(":stub-source"))
    assert ":silicon-bringup:silicon-bringup" in incoming.scene_id
    assert outgoing.scene_id.startswith(
        f"relation:{outgoing_id}:silicon-bringup:silicon-bringup:")
    assert incoming.points and outgoing.points

    # Reconstruct the completed source mark and its connected comparison-host
    # cluster from Scene geometry. The start endpoint has one legal egress:
    # outward through that named comparison corridor. Above/below would slide
    # along the primary start end-face and are rejected by the same closed-bound
    # validator used by Layout before routing.
    bringup_marks = [item for item in primitives
                     if item.source_ref == "silicon-bringup"
                     and item.purpose in {"planned", "actual", "snapshot"}
                     and item.bounds is not None]

    def mark_from_primitive(item):
        inline, block, inline_size, block_size = item.bounds
        bounds = Rect(*(Decimal(str(value)) for value in
                        (inline, block, inline_size, block_size)))
        center = (inline, block + block_size / 2)
        return MarkPlacement(item.scene_id, item.source_ref, bounds, center,
                             (inline + inline_size, center[1]), mark_shape="span")

    marks = tuple(mark_from_primitive(item) for item in bringup_marks)
    source_mark = next(item for item in marks
                       if item.placement_id == "planned:silicon-bringup:silicon-bringup")
    siblings = tuple(item for item in marks if item is not source_mark)
    egresses = connector_egress_candidates(
        source_mark, "start", (source_mark.start_port[0] - 1, source_mark.start_port[1]), siblings,
        explicit_neighbors=physical_host_neighbors(source_mark, marks, "start"),
    )
    assert {item.side for item in egresses} == {"start", "above", "below"}
    primary_bounds = tuple(
        (item.placement_id, ObstacleRect(
            float(item.bounds.inline), float(item.bounds.block),
            float(item.bounds.inline + item.bounds.inline_size),
            float(item.bounds.block + item.bounds.block_size),
        ))
        for item in marks
        if item.placement_id.startswith(("planned:", "actual:"))
        and ":snapshot:" not in item.placement_id
    )
    start_egress = next(item for item in egresses if item.side == "start")
    assert start_egress.exposed_port[0] < source_mark.start_port[0]
    assert "planned:silicon-bringup:snapshot:silicon-bringup" in start_egress.host_ids
    assert _primary_egress_blockers(start_egress, primary_bounds) == ()
    for side in ("above", "below"):
        candidate = next(item for item in egresses if item.side == side)
        assert "planned:silicon-bringup:silicon-bringup" in _primary_egress_blockers(
            candidate, primary_bounds,
        )

    # Both painted approaches occupy this same authorized semantic-to-exposed
    # corridor. This fixture therefore tests truthful label retention and the
    # diagnostic, not a no-overlap property that closed-contact safety makes
    # impossible. Clear-node alternatives remain covered by
    # test_relation_node_approach.py::test_departure_avoids_shared_approach_when_successor_precedes_gate.
    incoming_approach = ObstacleSegment(incoming.points[-2], incoming.points[-1])
    outgoing_approach = ObstacleSegment(outgoing.points[0], outgoing.points[1])
    corridor = (start_egress.semantic_port, start_egress.exposed_port)

    def segment_length(segment):
        return abs(segment[1][0] - segment[0][0]) + abs(segment[1][1] - segment[0][1])

    assert segment_overlap_length(
        (incoming_approach.start, incoming_approach.end), corridor,
    ) == segment_length((incoming_approach.start, incoming_approach.end))
    assert segment_overlap_length(
        (outgoing_approach.start, outgoing_approach.end), corridor,
    ) == segment_length((outgoing_approach.start, outgoing_approach.end))
    diagnostics = [item for item in rendered.scene.diagnostics
                   if item.startswith("I_LAYOUT_RELATION_NODE_APPROACH_SHARED:")]
    assert any(
        payload.get("nodeInstanceId") == "silicon-bringup:silicon-bringup"
        and set(payload.get("relationIds", ())) == {incoming.scene_id, outgoing.scene_id}
        for payload in (json.loads(item.split(":", 1)[1]) for item in diagnostics)
    )
