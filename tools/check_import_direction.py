"""Report imports that cross a layer boundary the wrong way.

Dependencies point inward. Each package may import the packages listed for it
below and nothing else; an import not covered by the table, or any cycle
between packages, fails. Adding an edge is a deliberate edit here, with the
reason in the commit that adds it.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"

# package -> packages it may import. Absent means "imports nothing else".
ALLOWED: dict[str, set[str]] = {
    # Adapters: may reach any use case, and the ports they wire up.
    "app": {"usecases", "core", "operational", "presentation", "scheduling", "storage", "resources"},
    # Use cases: own one pipeline each, across the layers below them.
    "usecases": {"core", "extensions", "presentation", "scheduling", "storage", "resources", "schema_diagnostics"},
    "operational": {"core", "commands", "usecases", "storage", "resources", "schema_diagnostics"},
    "release": {"core", "presentation", "resources"},
    "collaboration": {"core", "storage", "resources"},
    "commands": {"core", "extensions", "scheduling", "storage", "resources"},
    # Domain services and adapters.
    # Structural ingress explanations are shared only by the two validation
    # boundaries; successful presentation layers never receive them.
    "presentation": {"core", "resources", "schema_diagnostics"},
    "scheduling": {"core", "resources"},
    "storage": {"core", "scheduling", "resources"},
    "extensions": {"core", "resources", "schema_diagnostics"},
    # The shared kernel depends on nothing but its own packaged schemas.
    "core": {"resources", "schema_diagnostics"},
    "resources": set(),
}


def package_of(module: str) -> str:
    parts = module.split(".")
    if len(parts) == 2 and parts[1] == "__main__":
        return "chrona"
    return parts[1] if len(parts) > 1 else parts[0]


def imports(path: Path, package: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package if node.level == 1 else package.rsplit(".", node.level - 1)[0]
                found.add(f"{base}.{node.module}" if node.module else base)
            elif node.module and node.module.startswith("chrona"):
                found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(name.name for name in node.names if name.name.startswith("chrona"))
    return found


def main() -> int:
    violations: list[str] = []
    edges: dict[str, set[str]] = {}
    for path in sorted((SOURCE / "chrona").rglob("*.py")):
        module = path.relative_to(SOURCE).as_posix().replace("/", ".")[:-3].removesuffix(".__init__")
        package = package_of(module)
        if package == "chrona":
            continue
        for target in imports(path, module if path.name == "__init__.py" else module.rsplit(".", 1)[0]):
            other = package_of(target)
            if other in {package, "chrona"}:
                continue
            edges.setdefault(package, set()).add(other)
            if other not in ALLOWED.get(package, set()):
                violations.append(f"{path.relative_to(ROOT)}: chrona.{package} must not import chrona.{other}")

    for package, targets in sorted(edges.items()):
        for other in sorted(targets):
            if package in edges.get(other, set()) and package < other:
                violations.append(f"cycle: chrona.{package} <-> chrona.{other}")

    for line in sorted(set(violations)):
        print(line)
    if violations:
        print("\nDependencies point inward; see the table in tools/check_import_direction.py.")
        return 1
    print(f"{len(edges)} packages, {sum(len(t) for t in edges.values())} edges, all inward")
    return 0


if __name__ == "__main__":
    sys.exit(main())
