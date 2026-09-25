"""Keep production and tooling YAML decoding on the fast safe-loader path."""
from __future__ import annotations

import ast
from pathlib import Path


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_production_and_tools_do_not_bypass_the_safe_yaml_loader():
    offenders = []
    for directory in (_root() / "src", _root() / "tools"):
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name) and node.func.value.id == "yaml"
                        and node.func.attr == "safe_load"):
                    offenders.append(path.relative_to(_root()).as_posix())
    assert offenders == []
