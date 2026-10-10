"""Corpus manifests must not be decoded as a side effect of importing tests."""
from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
IMPORT_MODULES = (
    "tests.acceptance.output.test_public_geometry_regressions",
    "tests.acceptance.output.test_generated_output_properties",
    "tests.acceptance.output.test_closure_inputs_are_read",
    "tests.integration.test_view_v01_schema",
)
CORPUS_LOADERS = {"declared_slides", "reachable_view_paths", "manifest_targets"}


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


class _ModuleScopeCalls(ast.NodeVisitor):
    """Visit executed module/class expressions, decorators and defaults."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = _called_name(node)
        if name:
            constants = tuple(item.value for item in ast.walk(node) if isinstance(item, ast.Constant)
                              and isinstance(item.value, str))
            self.calls.append((name, constants))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for value in (*node.args.defaults, *node.args.kw_defaults):
            if value is not None:
                self.visit(value)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        for statement in node.body:
            self.visit(statement)


def _imported_loader_aliases(tree: ast.Module) -> set[str]:
    aliases = set(CORPUS_LOADERS)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            aliases.update(alias.asname or alias.name for alias in node.names if alias.name in CORPUS_LOADERS)
    return aliases


def _eager_corpus_helpers(tree: ast.Module) -> set[str]:
    """Find local helpers which parse a manifest and are called from module scope."""
    functions = {node.name: node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    helpers: set[str] = set()
    loaders = _imported_loader_aliases(tree)
    for name, node in functions.items():
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = {_called_name(item) for item in ast.walk(node) if isinstance(item, ast.Call)}
        constants = [item.value for item in ast.walk(node) if isinstance(item, ast.Constant)
                     and isinstance(item.value, str)]
        manifest_scan = any("manifest.yaml" in value and "examples" in value for value in constants)
        if (calls & loaders
                or (manifest_scan and bool(calls & {"safe_load", "safe_load_all", "load"}))):
            helpers.add(name)
    changed = True
    while changed:
        changed = False
        for name, node in functions.items():
            calls = {_called_name(item) for item in ast.walk(node) if isinstance(item, ast.Call)}
            if name not in helpers and calls & helpers:
                helpers.add(name)
                changed = True
    return helpers


@pytest.mark.parametrize("source", [
    "from x import declared_slides as discover\nresult = discover()",
    "class Cases:\n    rows = declared_slides()",
    "@decorate(reachable_view_paths())\ndef test_case(): pass",
    "def test_case(rows=manifest_targets()): pass",
    "from x import declared_slides as discover\ndef first(): return discover()\n"
    "def second(): return first()\nrows = second()",
])
def test_source_guard_detects_executable_scopes_aliases_and_helper_chains(source):
    tree = ast.parse(source)
    calls = _ModuleScopeCalls()
    calls.visit(tree)
    forbidden = _imported_loader_aliases(tree) | _eager_corpus_helpers(tree)
    assert any(name in forbidden for name, _ in calls.calls)


def test_test_sources_have_no_module_scope_corpus_loader_calls() -> None:
    offenders = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        loaders = _imported_loader_aliases(tree)
        helpers = _eager_corpus_helpers(tree)
        calls = _ModuleScopeCalls()
        for node in tree.body:
            calls.visit(node)
        bad = sorted({name for name, constants in calls.calls
                      if name in loaders | helpers | {"_slides"}
                      or (name == "glob" and any("manifest.yaml" in value and "examples" in value
                                                   for value in constants))
                      or (name in {"safe_load", "safe_load_all", "load"}
                          and any("manifest.yaml" in value and "examples" in value for value in constants))})
        if bad:
            offenders.append(f"{path.relative_to(ROOT).as_posix()}: {', '.join(bad)}")
    assert offenders == [], "corpus discovery/loading at module import:\n" + "\n".join(offenders)


def test_importing_corpus_test_modules_does_not_read_example_yaml(tmp_path: Path) -> None:
    script = r'''
import importlib
from pathlib import Path

def _is_example_path(path):
    return "examples" in path.parts and path.suffix.lower() in {".yaml", ".yml"}

for method_name in ("read_bytes", "read_text"):
    original = getattr(Path, method_name)
    def guarded(self, *args, _original=original, _method=method_name, **kwargs):
        if _is_example_path(self):
            raise AssertionError(f"example YAML read during import: {self}")
        return _original(self, *args, **kwargs)
    setattr(Path, method_name, guarded)

original_glob = Path.glob
def guarded_glob(self, pattern):
    if "examples" in self.parts and "manifest.yaml" in pattern:
        raise AssertionError(f"manifest discovery during import: {self}/{pattern}")
    return original_glob(self, pattern)
Path.glob = guarded_glob

import tools.derived_evidence as derived
import tools.check_example_reachability as reachability
import tests.support.public_evidence as evidence
def forbidden(*args, **kwargs):
    raise AssertionError("corpus discovery helper called during import")
derived.manifest_targets = forbidden
reachability.reachable_view_paths = forbidden
evidence.declared_slides = forbidden

for module in MODULES:
    importlib.import_module(module)
'''.replace("MODULES", repr(IMPORT_MODULES))
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, text=True,
                            capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
