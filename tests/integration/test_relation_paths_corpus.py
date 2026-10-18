"""Corpus twin of tests/unit/chrona/presentation/scene/test_relation_ghost_endpoints.py (#1031).

The slides that draw baseline or scenario ghosts are rendered in the test (no committed Scene is edited or trusted)
and must show every relation once, between current plan marks. The whole corpus is also guarded by the
`E_SCENE_RELATION_PATH_DUPLICATE` perceptibility error that `conformance` runs over every manifest Scene.
"""
from collections import Counter
import json
from pathlib import Path

import pytest

from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.scene.serialization import serialize_scene
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
        own = [node] if node.get("kind") == "Path" and str(node.get("id", "")).startswith("relation:") else []
        return own + [path for value in node.values() for path in _relation_paths(value)]
    if isinstance(node, list):
        return [path for value in node for path in _relation_paths(value)]
    return []


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
    paths = _relation_paths(scene)

    assert len(paths) == relations
    assert max(Counter(path["sourceRef"] for path in paths).values()) == 1
    assert not [path["id"] for path in paths if "snapshot:" in path["id"] or "scenario:" in path["id"]]
