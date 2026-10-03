"""Corpus twin of the entry-side rules (#1072, #1084); the synthetic twins are in
tests/unit/chrona/presentation/layout/test_stub_pair_order.py and
tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py.

Target B is rendered in the test (no committed Scene is trusted or edited). Whatever entry policy its Layout declares
(`side-when-free` or `side`), `optics-detector` must enter the detector's start horizontally and no relation path may
overlap itself.
"""
import json
from pathlib import Path

import pytest

from tools.materialize_example import materialize

ROOT = Path(__file__).resolve().parents[2]


def _relation_paths(node) -> list[dict]:
    if isinstance(node, dict):
        own = [node] if node.get("kind") == "Path" and str(node.get("id", "")).startswith("relation:") else []
        return own + [path for value in node.values() for path in _relation_paths(value)]
    if isinstance(node, list):
        return [path for value in node for path in _relation_paths(value)]
    return []


@pytest.mark.corpus
def test_target_b_optics_detector_enters_the_start_horizontally(tmp_path):
    materialize(ROOT / "examples/halcyon-1/manifest.yaml", "target-b", tmp_path / "target-b", write=False)
    paths = {path["sourceRef"]: path["points"] for path in
             _relation_paths(json.loads((tmp_path / "target-b/review.scene.json").read_text(encoding="utf-8")))}
    points = paths["optics-detector"]
    assert points[-2][1] == points[-1][1] and points[-2][0] < points[-1][0]
    for relation, relation_points in paths.items():
        for a, b, c in zip(relation_points, relation_points[1:], relation_points[2:]):
            collinear = (a[0] == b[0] == c[0] and (b[1] - a[1]) * (c[1] - b[1]) < 0) or (
                a[1] == b[1] == c[1] and (b[0] - a[0]) * (c[0] - b[0]) < 0)
            assert not collinear, relation
