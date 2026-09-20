"""Architecture assertions for the public package dependency direction."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SOURCE = ROOT / "src" / "chrona"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_core_has_no_outward_runtime_dependencies():
    forbidden = (
        "chrona.storage",
        "chrona.extensions",
        "chrona.presentation",
        "chrona.app",
        "chrona.release",
    )
    violations = {
        str(path.relative_to(ROOT)): sorted(
            module for module in _imports(path) if module.startswith(forbidden)
        )
        for path in (SOURCE / "core").rglob("*.py")
    }
    assert not {path: modules for path, modules in violations.items() if modules}


def test_renderers_do_not_depend_on_review_orchestration():
    violations = {
        str(path.relative_to(ROOT)): sorted(
            module for module in _imports(path)
            if module.startswith("chrona.presentation.review")
        )
        for path in (SOURCE / "presentation" / "renderers").rglob("*.py")
    }
    assert not {path: modules for path, modules in violations.items() if modules}
