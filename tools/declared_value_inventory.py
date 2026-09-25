#!/usr/bin/env python3
"""Inventory comparisons between declared values and computed identities."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
import shlex
import tempfile
from typing import Any, Iterable, Mapping

import yaml

from chrona.resources import safe_load


POLICY_VERSION = "chrona/resolvability-quality-policy/v0.1"
CLASSIFICATIONS = {"pinned-deliberately", "product-bookkeeping"}
DECLARED_FIELDS = {"baseRevision", "contentIdentity", "requestIdentity", "targetIdentity"}


class DeclaredValueInventoryError(ValueError):
    """A declared/computed classification is absent or invalid."""


@dataclass(frozen=True, order=True)
class ComparisonSite:
    path: str
    function: str
    field: str
    line: int
    declared: str
    computed: str

    @property
    def anchor(self) -> tuple[str, str, str]:
        return self.path, self.function, self.field


def _identity_expression(node: ast.AST, names: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in names
    if isinstance(node, ast.Call):
        label = ast.unparse(node.func)
        return (label.endswith(("content_identity", "_identity", ".sha256")) or label == "sha256"
                or any(_identity_expression(child, names) for child in ast.iter_child_nodes(node)))
    return any(_identity_expression(child, names) for child in ast.iter_child_nodes(node))


def _field(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
        value = node.args[0]
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
    if isinstance(node, ast.Subscript):
        value = node.slice
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
    if isinstance(node, ast.Attribute) and "identity" in node.attr.lower():
        return {"content_identity": "contentIdentity"}.get(node.attr, node.attr)
    return None


def _computed_names(function: ast.AST) -> set[str]:
    names: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in ast.walk(function):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None and _identity_expression(node.value, names):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in names:
                        names.add(target.id); changed = True
    return names


def _function_sites(function: ast.AST, path: str, name: str) -> Iterable[ComparisonSite]:
    computed_names = _computed_names(function)
    for node in ast.walk(function):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1 or not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
            continue
        left, right = node.left, node.comparators[0]
        left_field, right_field = _field(left), _field(right)
        if left_field in DECLARED_FIELDS and _identity_expression(right, computed_names):
            declared, computed, field = left, right, left_field
        elif right_field in DECLARED_FIELDS and _identity_expression(left, computed_names):
            declared, computed, field = right, left, right_field
        else:
            continue
        yield ComparisonSite(path, name, field, node.lineno, ast.unparse(declared), ast.unparse(computed))


def discover(root: Path) -> tuple[ComparisonSite, ...]:
    sites: list[ComparisonSite] = []
    for source_path in sorted((root / "src" / "chrona").rglob("*.py")):
        path = source_path.relative_to(root).as_posix()
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sites.extend(_function_sites(node, path, node.name))
    return tuple(sorted(set(sites)))


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeclaredValueInventoryError(code)
    return value


def load_policy(path: Path) -> tuple[Mapping[str, Any], ...]:
    try:
        document = _mapping(safe_load(path.read_bytes()), "E_DECLARED_VALUE_POLICY_DOCUMENT")
    except (OSError, yaml.YAMLError) as error:
        raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_READ") from error
    if document.get("version") != POLICY_VERSION:
        raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_VERSION")
    entries = document.get("declaredComputedValues")
    if not isinstance(entries, list):
        raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_ENTRIES")
    result: list[Mapping[str, Any]] = []
    for entry in entries:
        entry = _mapping(entry, "E_DECLARED_VALUE_POLICY_ENTRY")
        if not all(isinstance(entry.get(key), str) and entry[key] for key in ("path", "function", "field", "classification")):
            raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_ENTRY")
        if entry["classification"] not in CLASSIFICATIONS:
            raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_CLASSIFICATION")
        producer, resolver = entry.get("producer"), entry.get("resolver")
        if entry["classification"] == "pinned-deliberately" and (not isinstance(producer, str) or not producer):
            raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_PRODUCER")
        if entry["classification"] == "product-bookkeeping" and (producer is not None or not isinstance(resolver, str) or not resolver):
            raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_BOOKKEEPING")
        result.append(entry)
    return tuple(result)


def command_paths() -> set[str]:
    from chrona.app.cli import _parser

    def children(parser: argparse.ArgumentParser, prefix: tuple[str, ...]) -> set[str]:
        result: set[str] = set()
        for action in parser._actions:  # argparse owns this authoritative metadata.
            if not isinstance(action, argparse._SubParsersAction):
                continue
            for name, child in action.choices.items():
                path = prefix + (name,)
                result.add("chrona " + " ".join(path))
                result |= children(child, path)
        return result

    return children(_parser(), ())


def validate(sites: tuple[ComparisonSite, ...], policy: tuple[Mapping[str, Any]]) -> None:
    indexed = {site.anchor: site for site in sites}
    policy_index = {(entry["path"], entry["function"], entry["field"]): entry for entry in policy}
    if len(policy_index) != len(policy):
        raise DeclaredValueInventoryError("E_DECLARED_VALUE_POLICY_DUPLICATE")
    unknown, missing = sorted(set(policy_index) - set(indexed)), sorted(set(indexed) - set(policy_index))
    if unknown or missing:
        detail = [*(f"unknown={'|'.join(item)}" for item in unknown), *(f"missing={'|'.join(item)}" for item in missing)]
        raise DeclaredValueInventoryError("E_DECLARED_VALUE_CLASSIFICATION\n" + "\n".join(detail))
    commands = command_paths()
    for entry in policy:
        command = entry.get("producer") or entry.get("resolver")
        if command not in commands:
            raise DeclaredValueInventoryError(f"E_DECLARED_VALUE_PRODUCER:{command}")


def render(sites: tuple[ComparisonSite, ...], policy: tuple[Mapping[str, Any]] = ()) -> str:
    classifications = {(entry["path"], entry["function"], entry["field"]): entry for entry in policy}
    lines = [
        "# Declared-versus-computed value inventory",
        "",
        "Generated by `tools/declared_value_inventory.py`; it records static identity comparisons that require an explicit product decision.",
        "",
        "| Source | Declared field | Computed expression | Classification | Producer |",
        "| --- | --- | --- | --- | --- |",
    ]
    for site in sites:
        entry = classifications.get(site.anchor, {})
        lines.append(
            f"| `{site.path}:{site.line}` ({site.function}) | `{site.field}` | `{site.computed}` | "
            f"{entry.get('classification', 'unclassified')} | {entry.get('producer', entry.get('resolver', '—'))} |"
        )
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
    parser.add_argument("--output", type=Path, default=Path("docs/diagnostics/declared-value-inventory.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(); root = args.root.resolve()
    policy_path = args.policy if args.policy.is_absolute() else root / args.policy
    output = args.output if args.output.is_absolute() else root / args.output
    sites, policy = discover(root), load_policy(policy_path)
    content = render(sites, policy)
    if args.check:
        validate(sites, policy)
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise SystemExit("E_DECLARED_VALUE_INVENTORY_STALE")
        return
    write(output, content)


if __name__ == "__main__":
    main()
