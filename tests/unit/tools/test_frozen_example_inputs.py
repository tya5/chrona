"""Retiring public examples cannot remain explicit test/tool dependencies."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RETIRED = {"controller-z", "controller-z-ja", "aster-ssd", "attached-milestones"}


def test_retired_examples_are_not_explicit_test_or_probe_inputs():
    sources = [*ROOT.glob("tests/**/*.py"), ROOT / "tools/schema_equivalence.py",
               ROOT / "tools/generate_controller_z_icon_catalog.py"]
    stale = []
    for source in sources:
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any("examples/" + name in node.value for name in RETIRED):
                    stale.append((source.relative_to(ROOT).as_posix(), node.lineno))
    assert not stale, stale
