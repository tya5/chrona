"""Retiring public examples cannot remain explicit test/tool dependencies."""
import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
RETIRED = {"controller-z", "controller-z-ja", "aster-ssd", "attached-milestones"}


def _path_parts(node):
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _path_parts(node.left) + _path_parts(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def _retired_reference(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if any("examples/" + name in node.value for name in RETIRED):
            return True
    parts = _path_parts(node)
    return any(left == "examples" and right in RETIRED
               for left, right in zip(parts, parts[1:]))


def test_retired_examples_are_not_explicit_test_or_probe_inputs():
    sources = [*ROOT.glob("tests/**/*.py"), ROOT / "tools/schema_equivalence.py",
               ROOT / "tools/generate_controller_z_icon_catalog.py"]
    stale = []
    for source in sources:
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if _retired_reference(node):
                stale.append((source.relative_to(ROOT).as_posix(), node.lineno))
    assert not stale, stale


@pytest.mark.parametrize("prefix,expected", [("examples", True), ("tests/fixtures", False)])
def test_guard_detects_split_paths_without_rejecting_fixtures(prefix, expected):
    source = f'root / "{prefix}" / "controller-z" / "project.yaml"'
    assert any(_retired_reference(node) for node in ast.walk(ast.parse(source))) is expected
