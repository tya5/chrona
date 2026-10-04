"""Corpus twin of the entry-side rules (#1072, #1084); the synthetic twins are in
tests/unit/chrona/presentation/layout/test_stub_pair_order.py and
tests/unit/chrona/presentation/scene/test_relation_entry_back_route.py.

Target B is rendered in the test (no committed Scene is trusted or edited). Whatever entry policy its Layout declares
(`side-when-free` or `side`), `optics-detector` must enter the detector's start horizontally and no relation path may
overlap itself.
"""
import json
import shutil
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


@pytest.mark.corpus
def test_target_b_with_entry_side_enters_from_the_side_or_says_why(tmp_path):
    # Target B (the reviewer's YAML, not edited) declares `entry: side` itself since #1061; the test renders a copy of
    # the corpus as committed and checks the same property (#1084).
    copy = tmp_path / "halcyon-1"
    shutil.copytree(ROOT / "examples/halcyon-1", copy)
    layout = copy / "layouts/target-b.yaml"
    assert "entry: side}" in layout.read_text(encoding="utf-8")
    materialize(copy / "manifest.yaml", "target-b", tmp_path / "out", write=True)
    scene = json.loads((tmp_path / "out/review.scene.json").read_text(encoding="utf-8"))
    paths = {path["sourceRef"]: path["points"] for path in _relation_paths(scene)}
    reasons = {line.split(":")[2]: line.partition(";reason=")[2]
               for line in scene["diagnostics"] if line.startswith("I_LAYOUT_RELATION_ENTRY_FALLBACK:")}
    sideways = {relation for relation, points in paths.items() if points[-2][1] == points[-1][1]}
    assert paths and sideways, "the declared context must emit actual relations, including side entries"
    exceptions = set(paths) - sideways
    assert exceptions <= set(reasons), "every relation that does not enter from the side carries a diagnostic"
    final_codes = {"same-row", "entry-stub-blocked", "degenerate", "bends-or-detour", "forward-entry-failed",
                   "terminal-axis-blocked", "sub-stroke-segment", "primary-mark-blocked"}
    assert all(reasons[relation] in final_codes or (
                   reasons[relation].startswith("blocked:") and reasons[relation].removeprefix("blocked:"))
               for relation in exceptions), {relation: reasons[relation] for relation in exceptions}
