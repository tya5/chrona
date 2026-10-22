"""Corpus twin of tests/unit/chrona/presentation/scene/test_relation_ghost_endpoints.py (#1031).

The slides that draw baseline or scenario ghosts are rendered in the test (no committed Scene is edited or trusted)
and must show every logical relation once, between current plan marks. A decoration halo is not another relation;
an explicitly receipted pair of endpoint stubs is one logical relation. The whole corpus is also guarded by the
`E_SCENE_RELATION_PATH_DUPLICATE` perceptibility error that `conformance` runs over every manifest Scene.
"""
import json
from pathlib import Path

import pytest

from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.scene.serialization import serialize_scene
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.materialize import copy_context_closure
from chrona.usecases.render_review import RenderRequest, render_review
from tools.materialize_example import materialize

ROOT = Path(__file__).resolve().parents[2]
GHOST_SLIDES = (("halcyon-1", "target-b", 24), ("halcyon-1", "tvac-slip", 4),
                ("halcyon-1", "flight-readiness", 1), ("controller-z", "baseline-ghosts", 7))


def _relation_paths(node) -> list[dict]:
    if isinstance(node, dict):
        own = [node] if (node.get("kind") == "Path" and node.get("sourceKind") == "relation"
                         and str(node.get("id", "")).startswith("relation:")) else []
        return own + [path for value in node.values() for path in _relation_paths(value)]
    if isinstance(node, list):
        return [path for value in node for path in _relation_paths(value)]
    return []


def _assert_logical_relations(scene, relations):
    paths = _relation_paths(scene)
    assert len({path["sourceRef"] for path in paths}) == relations
    duplicates = [finding for finding in evaluate_scene_perceptibility(scene)
                  if finding.code == "E_SCENE_RELATION_PATH_DUPLICATE"]
    assert not duplicates, duplicates
    assert not [path["id"] for path in paths if "snapshot:" in path["id"] or "scenario:" in path["id"]]
    assert not [path for path in paths for key in ("fromInstanceId", "toInstanceId")
                if str(path.get(key, "")).startswith(("snapshot:", "scenario:"))]


def _synthetic_scene(*identifiers, receipt=False, halo=False):
    bounds = {"inline": 0, "block": 0, "inlineSize": 20, "blockSize": 20}
    paths = [{"id": identifier, "kind": "Path", "sourceKind": "relation", "sourceRef": "dep",
              "slotId": "timeline", "bounds": bounds, "points": [[1, 1], [9, 1]]}
             for identifier in identifiers]
    if halo:
        paths.append({**paths[0], "id": identifiers[0] + ":halo", "sourceKind": "decoration",
                      "purpose": "dependency-halo"})
    diagnostics = []
    if receipt:
        diagnostics.append("I_LAYOUT_RELATION_RESOLUTION:" + json.dumps({
            "surfaceId": "review", "relationId": "relation:dep", "stage": "stub",
            "critical": False, "fragmentIds": list(identifiers[:2])}))
    return {"version": "chrona/scene/v0.6", "kind": "scene", "diagnostics": diagnostics,
            "surfaces": [{"id": "review", "slots": [{"id": "timeline", "bounds": bounds, "overflow": "fit"}],
                          "primitives": paths}]}


def test_corpus_relation_observation_excludes_decorative_halo():
    scene = _synthetic_scene("relation:dep:a:b", halo=True)
    assert len(_relation_paths(scene)) == 1
    _assert_logical_relations(scene, 1)


def test_corpus_relation_observation_accepts_only_receipted_stub_pair():
    scene = _synthetic_scene("relation:fragment-a", "relation:fragment-b", receipt=True, halo=True)
    assert len(_relation_paths(scene)) == 2
    _assert_logical_relations(scene, 1)


@pytest.mark.parametrize("receipt,extra", [(False, ()), (True, ("relation:third",))])
def test_corpus_logical_count_still_rejects_duplicate_paths(receipt, extra):
    scene = _synthetic_scene("relation:a", "relation:b", *extra, receipt=receipt)
    with pytest.raises(AssertionError, match="E_SCENE_RELATION_PATH_DUPLICATE"):
        _assert_logical_relations(scene, 1)


@pytest.mark.parametrize("endpoint", ["snapshot:object", "scenario:object"])
def test_corpus_observation_still_rejects_ghost_endpoint_identity(endpoint):
    scene = _synthetic_scene("relation:dep:a:b")
    scene["surfaces"][0]["primitives"][0].update(fromInstanceId=endpoint, toInstanceId="plan:b")
    with pytest.raises(AssertionError):
        _assert_logical_relations(scene, 1)


@pytest.mark.corpus
@pytest.mark.parametrize(("example", "slide", "relations"), GHOST_SLIDES)
def test_a_slide_with_ghosts_draws_each_relation_once_between_plan_marks(tmp_path, example, slide, relations):
    if example == "controller-z":
        fixture = ROOT / "tests/fixtures/controller-z"
        snapshot = tmp_path / "snapshot"
        reference, _ = copy_context_closure(
            fixture, fixture / "contexts/baseline-ghosts.yaml", snapshot,
        )
        # Retired, unpinned fixture output is not a current byte oracle.
        # Render its unchanged Context and inspect the completed relation paths.
        closure = resolve_render_context(reference, LocalSnapshotReader(
            snapshot, "controller-z-example", require_content_identity=False,
        ))
        rendered = render_review(RenderRequest(closure, snapshot, ReferenceScheduler()))
        scene = json.loads(serialize_scene(rendered.scene))
    else:
        materialize(ROOT / "examples" / example / "manifest.yaml", slide, tmp_path / slide, write=False)
        scene = json.loads((tmp_path / slide / "review.scene.json").read_text(encoding="utf-8"))
    _assert_logical_relations(scene, relations)
