"""Public Controller evidence for retained relation labels and their shared-node routes (#1158)."""
from __future__ import annotations

from pathlib import Path
import yaml
import xml.etree.ElementTree as ET

from chrona.presentation.layout.obstacles import ObstacleSegment, obstacles_intersect
from chrona.core.relation_identity import relation_identity
from chrona.usecases.materialize import materialize


ROOT = Path(__file__).resolve().parents[2]
SVG_NS = "{http://www.w3.org/2000/svg}"


def test_controller_baseline_ghosts_emits_start_start_label_without_shared_node_route_overlap(tmp_path):
    result = materialize(
        ROOT / "tests/fixtures/controller-z/manifest.yaml", "baseline-ghosts",
        tmp_path / "controller-baseline-ghosts", write=False,
    )
    rendered = result.rendered
    svg = ET.fromstring(rendered.artifact.content)
    project = yaml.safe_load((ROOT / "examples/controller-z/project.yaml").read_bytes())
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
