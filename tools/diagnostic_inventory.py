#!/usr/bin/env python3
"""Derive and check literal diagnostic construction evidence."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping

import yaml


POLICY_VERSION = "chrona/resolvability-quality-policy/v0.1"
DIAGNOSTIC_CODE = re.compile(r"^[EW]_[A-Z0-9_]+$")
DISPOSITIONS = {"sufficient", "backlog"}


class DiagnosticInventoryError(ValueError):
    """The quality-policy input or source population is invalid."""


@dataclass(frozen=True, order=True)
class DiagnosticSite:
    code: str
    path: str
    line: int
    column: int
    function: str
    constructor: str
    layer: str
    has_detail: bool

    @property
    def anchor(self) -> str:
        return f"{self.path}:{self.line}:{self.column}"


def _literal_code(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.split(":", 1)[0]
        return value if DIAGNOSTIC_CODE.fullmatch(value) else None
    return None


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    return type(node).__name__


def _function_names(tree: ast.AST) -> dict[int, str]:
    names: dict[int, str] = {}

    def visit(node: ast.AST, enclosing: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = enclosing
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = child.name
            names[id(child)] = name
            visit(child, name)

    names[id(tree)] = "<module>"
    visit(tree, "<module>")
    return names


def _modules(root: Path) -> dict[str, Path]:
    source = root / "src"
    found = {}
    for path in (source / "chrona").rglob("*.py"):
        name = path.relative_to(source).as_posix().replace("/", ".")[:-3]
        found[name.removesuffix(".__init__")] = path
    return found


def _imports(path: Path, package: str, known: set[str]) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package if node.level == 1 else package.rsplit(".", node.level - 1)[0]
                target = f"{base}.{node.module}" if node.module else base
            elif node.module and node.module.startswith("chrona"):
                target = node.module
            else:
                continue
            found.add(target)
            found.update(f"{target}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("chrona"))
    return {name for name in found if name in known}


def cli_reachable_modules(root: Path) -> set[str]:
    modules = _modules(root)
    known = set(modules)
    graph = {
        name: _imports(path, name if path.name == "__init__.py" else name.rsplit(".", 1)[0], known)
        for name, path in modules.items()
    }
    reached: set[str] = set()
    stack = [name for name in ("chrona.app.cli", "chrona.__main__") if name in modules]
    while stack:
        name = stack.pop()
        if name in reached:
            continue
        reached.add(name)
        stack.extend(graph[name])
    return reached


def _calls(tree: ast.AST, path: str, *, layer: str) -> Iterable[DiagnosticSite]:
    functions = _function_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        code_index = next((index for index, value in enumerate(node.args) if _literal_code(value)), None)
        if code_index is None:
            continue
        code = _literal_code(node.args[code_index])
        assert code is not None
        detail_arguments = node.args[code_index + 1:]
        detail_keywords = [item for item in node.keywords if item.arg in {"detail", "message", "path", "source_ref"}]
        yield DiagnosticSite(
            code=code,
            path=path,
            line=node.lineno,
            column=node.col_offset,
            function=functions.get(id(node), "<module>"),
            constructor=_name(node.func),
            layer=layer,
            has_detail=bool(detail_arguments or detail_keywords),
        )


def discover(root: Path) -> tuple[DiagnosticSite, ...]:
    source = root / "src" / "chrona"
    reachable = cli_reachable_modules(root)
    sites: list[DiagnosticSite] = []
    for source_path in sorted(source.rglob("*.py")):
        path = source_path.relative_to(root).as_posix()
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=path)
        module = path.removeprefix("src/").replace("/", ".").removesuffix(".py").removesuffix(".__init__")
        sites.extend(_calls(tree, path, layer="user-facing-ingress" if module in reachable else "internal"))
    return tuple(sorted(sites))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DiagnosticInventoryError(f"E_DIAGNOSTIC_POLICY_{label}")
    return value


def load_policy(path: Path) -> tuple[Mapping[str, Any], ...]:
    try:
        document = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "DOCUMENT")
    except (OSError, yaml.YAMLError) as error:
        raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_READ") from error
    if document.get("version") != POLICY_VERSION:
        raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_VERSION")
    actionability = _mapping(document.get("diagnosticActionability"), "ACTIONABILITY")
    bare = actionability.get("bareDiagnostics")
    if not isinstance(bare, list):
        raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_BARE")
    default = _mapping(actionability.get("defaultBacklog"), "DEFAULT_BACKLOG")
    if default.get("disposition") != "backlog" or not isinstance(default.get("nextAction"), str) or not default["nextAction"].strip():
        raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_DEFAULT_BACKLOG")
    entries: list[Mapping[str, Any]] = []
    for entry in bare:
        entry = _mapping(entry, "ENTRY")
        disposition = entry.get("disposition")
        if not isinstance(entry.get("code"), str) or not DIAGNOSTIC_CODE.fullmatch(entry["code"]) or disposition not in DISPOSITIONS:
            raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_ENTRY")
        if disposition == "sufficient" and (not isinstance(entry.get("reason"), str) or not entry["reason"].strip()):
            raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_ENTRY")
        if disposition == "backlog" and (not isinstance(entry.get("nextAction"), str) or not entry["nextAction"].strip()):
            raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_ENTRY")
        entries.append(entry)
    return (*entries, {"code": "*", **default})


def validate(sites: tuple[DiagnosticSite, ...], policy: tuple[Mapping[str, Any], ...]) -> None:
    bare = {site.code for site in sites if site.layer == "user-facing-ingress" and not site.has_detail}
    classified = {str(entry["code"]) for entry in policy if entry["code"] != "*"}
    if len(classified) != len(policy) - 1:
        raise DiagnosticInventoryError("E_DIAGNOSTIC_POLICY_DUPLICATE")
    unknown = sorted(classified - bare)
    missing: list[str] = []
    if unknown or missing:
        detail = [*(f"unknown={item}" for item in unknown), *(f"missing={item}" for item in missing)]
        raise DiagnosticInventoryError("E_DIAGNOSTIC_ACTIONABILITY\n" + "\n".join(detail))


def render(sites: tuple[DiagnosticSite, ...], policy: tuple[Mapping[str, Any], ...]) -> str:
    lines = [
        "# Diagnostic inventory",
        "",
        "Generated by `tools/diagnostic_inventory.py`; this report derives literal diagnostic construction sites from `src/chrona`.",
        "",
        "| Code | Layer | Detail | Constructor | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for site in sites:
        detail = "yes" if site.has_detail else "no"
        lines.append(f"| `{site.code}` | {site.layer} | {detail} | `{site.constructor}` | `{site.anchor}` ({site.function}) |")
    bare = [site for site in sites if site.layer == "user-facing-ingress" and not site.has_detail]
    entries = {str(entry["code"]): entry for entry in policy}
    default = entries.pop("*")
    backlog = [(code, sum(site.code == code for site in bare), entry["nextAction"])
               for code, entry in sorted(entries.items()) if entry["disposition"] == "backlog"]
    backlog.extend((code, sum(site.code == code for site in bare), default["nextAction"])
                   for code in sorted({site.code for site in bare} - set(entries)))
    lines.extend(["", "## Actionability backlog", "", "| Code | Bare reachable sites | Next action |", "| --- | ---: | --- |"])
    lines.extend(f"| `{code}` | {count} | {action} |" for code, count, action in sorted(backlog, key=lambda item: (-item[1], item[0])))
    if not backlog:
        lines.append("None.")
    lines.extend(["", "## Bare user-facing constructions", ""])
    lines.extend(f"- `{site.anchor}` — `{site.code}` in `{site.function}`" for site in bare)
    if not bare:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--policy", type=Path, default=Path("conformance/resolvability-quality-policy-v0.1.yaml"))
    parser.add_argument("--output", type=Path, default=Path("docs/diagnostics/inventory.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    policy_path = args.policy if args.policy.is_absolute() else root / args.policy
    output = args.output if args.output.is_absolute() else root / args.output
    sites = discover(root)
    policy = load_policy(policy_path)
    content = render(sites, policy)
    if args.check:
        validate(sites, policy)
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise SystemExit("E_DIAGNOSTIC_INVENTORY_STALE")
        return
    write(output, content)


if __name__ == "__main__":
    main()
