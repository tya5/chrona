"""Layering of the terse plan syntax (#148): `chrona.terse` imports only `core`, and only `usecases` may import it."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tools import check_import_direction as tool

SOURCE = Path(__file__).resolve().parents[3] / "src" / "chrona"


def test_the_table_has_the_terse_row_and_the_single_new_edge():
    assert tool.ALLOWED["terse"] == {"core"}
    allowed_by = sorted(package for package, targets in tool.ALLOWED.items() if "terse" in targets)
    assert allowed_by == ["usecases"]


def test_terse_imports_nothing_but_core_and_itself():
    seen: set[str] = set()
    for path in sorted((SOURCE / "terse").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("chrona"):
                seen.add(node.module.split(".")[1])
            elif isinstance(node, ast.Import):
                seen.update(name.name.split(".")[1] for name in node.names if name.name.startswith("chrona."))
    assert seen <= {"core", "terse"}, seen


def test_only_the_use_case_reaches_terse_from_outside():
    importers = set()
    for path in sorted(SOURCE.rglob("*.py")):
        relative = path.relative_to(SOURCE)
        if relative.parts[0] == "terse":
            continue
        if "chrona.terse" in path.read_text(encoding="utf-8"):
            importers.add(relative.as_posix())
    assert importers == {"usecases/terse_compile.py"}


def _tree(tmp_path: Path, package: str) -> Path:
    root = tmp_path / "src" / "chrona"
    for name in ("terse", package):
        (root / name).mkdir(parents=True)
        (root / name / "__init__.py").write_text("", encoding="utf-8")
    (root / "terse" / "compiler.py").write_text("X = 1\n", encoding="utf-8")
    return root


@pytest.mark.parametrize("package", ["storage", "presentation", "scheduling", "operational", "release", "app", "core"])
def test_a_forbidden_package_importing_terse_is_flagged(tmp_path, monkeypatch, capsys, package):
    root = _tree(tmp_path, package)
    (root / package / "uses.py").write_text("from chrona.terse.compiler import X\n", encoding="utf-8")
    monkeypatch.setattr(tool, "SOURCE", tmp_path / "src")
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    assert tool.main() == 1
    assert f"chrona.{package} must not import chrona.terse" in capsys.readouterr().out


def test_usecases_importing_terse_and_terse_importing_core_pass(tmp_path, monkeypatch):
    root = _tree(tmp_path, "usecases")
    (root / "core").mkdir()
    (root / "core" / "__init__.py").write_text("", encoding="utf-8")
    (root / "usecases" / "uses.py").write_text("from chrona.terse.compiler import X\n", encoding="utf-8")
    (root / "terse" / "compiler.py").write_text("from chrona.core import diagnostics\n", encoding="utf-8")
    monkeypatch.setattr(tool, "SOURCE", tmp_path / "src")
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    assert tool.main() == 0


def test_terse_importing_anything_else_is_flagged(tmp_path, monkeypatch, capsys):
    root = _tree(tmp_path, "scheduling")
    (root / "terse" / "compiler.py").write_text("from chrona.scheduling import x\n", encoding="utf-8")
    monkeypatch.setattr(tool, "SOURCE", tmp_path / "src")
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    assert tool.main() == 1
    assert "chrona.terse must not import chrona.scheduling" in capsys.readouterr().out
