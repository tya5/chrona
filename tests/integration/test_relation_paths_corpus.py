"""Corpus twin of tests/unit/chrona/presentation/scene/test_relation_ghost_endpoints.py (#1031).

The slides that draw baseline or scenario ghosts are rendered in the test (no committed Scene is edited or trusted)
and must show every relation once, between current plan marks. The whole corpus is also guarded by the
`E_SCENE_RELATION_PATH_DUPLICATE` perceptibility error that `conformance` runs over every manifest Scene.
"""
from collections import Counter
import json
from pathlib import Path

import pytest

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
    materialize(ROOT / "examples" / example / "manifest.yaml", slide, tmp_path / slide, write=False)
    paths = _relation_paths(json.loads((tmp_path / slide / "review.scene.json").read_text(encoding="utf-8")))

    assert len(paths) == relations
    assert max(Counter(path["sourceRef"] for path in paths).values()) == 1
    assert not [path["id"] for path in paths if "snapshot:" in path["id"] or "scenario:" in path["id"]]
