"""Frozen Context evidence for retained relation labels and shared-node routes (#1158)."""
from __future__ import annotations

from pathlib import Path
import yaml
import xml.etree.ElementTree as ET

from chrona.presentation.layout.obstacles import ObstacleSegment, obstacles_intersect
from chrona.core.relation_identity import relation_identity
from chrona.presentation.model.closure import resolve_render_context
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.materialize import copy_context_closure
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_controller_baseline_ghosts_emits_start_start_label_without_shared_node_route_overlap(tmp_path):
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
    identities = {relation["id"]: relation_identity(index, relation)
                  for index, relation in enumerate(project["relations"])}
    incoming_id = identities["evb-to-bringup"]
    outgoing_id = identities["bringup-to-performance"]

    label = next(node for node in svg.iter(SVG_NS + "text")
                 if node.attrib.get("data-scene-id", "").startswith(
                     f"relation-label:{outgoing_id}:"))
    assert label.text == "start->start"
    assert not any(item.startswith(f"W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:{outgoing_id}:")
                   for item in rendered.scene.diagnostics)

    primitives = rendered.scene.surfaces[0].primitives
    incoming = next(item for item in primitives
                    if item.scene_id.startswith(f"relation:{incoming_id}:"))
    outgoing = next(item for item in primitives
                    if item.scene_id.startswith(f"relation:{outgoing_id}:"))
    assert ":silicon-bringup:silicon-bringup" in incoming.scene_id
    assert outgoing.scene_id.startswith(
        f"relation:{outgoing_id}:silicon-bringup:silicon-bringup:")
    assert incoming.points and outgoing.points

    # The incoming terminal approach and outgoing source approach are distinct
    # completed segments. Their exact geometry must not cross or share a run.
    incoming_approach = ObstacleSegment(incoming.points[-2], incoming.points[-1])
    outgoing_approach = ObstacleSegment(outgoing.points[0], outgoing.points[1])
    assert not obstacles_intersect(incoming_approach, outgoing_approach)
