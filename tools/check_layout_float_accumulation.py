"""Reject unclassified builtin float accumulation in Layout placement code."""
from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "src/chrona/presentation/layout"

# These functions use an explicit Decimal seed or all-Decimal operands.  Their
# precision domain is intentionally different from completed float geometry.
DECIMAL_SUM_FUNCTIONS = {
    "dependency_network.py": frozenset({"_place_nodes"}),
    "engine.py": frozenset({"_allocate", "_measure_node", "_linear", "_grid", "_flow"}),
    "sources.py": frozenset({"measure_sources"}),
}


class _Sums(ast.NodeVisitor):
    def __init__(self, file_name: str) -> None:
        self.file_name = file_name
        self.function = "<module>"
        self.violations: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prior, self.function = self.function, node.name
        self.generic_visit(node)
        self.function = prior

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "sum" and not self._allowed(node):
            self.violations.append(f"{self.file_name}:{node.lineno}:E_LAYOUT_FLOAT_SUM_UNCLASSIFIED")
        self.generic_visit(node)

    def _allowed(self, node: ast.Call) -> bool:
        if self.function in DECIMAL_SUM_FUNCTIONS.get(self.file_name, frozenset()):
            return True
        if len(node.args) != 1 or node.keywords:
            return False
        value = node.args[0]
        if not isinstance(value, ast.GeneratorExp):
            return False
        return isinstance(value.elt, (ast.Compare, ast.BoolOp, ast.UnaryOp))


def violations(root: Path = LAYOUT) -> tuple[str, ...]:
    """Return stable failures for direct builtin sums outside reviewed classes."""
    found: list[str] = []
    for path in sorted(root.glob("*.py")):
        visitor = _Sums(path.name)
        visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
        found.extend(visitor.violations)
    return tuple(found)


def main() -> int:
    found = violations()
    if found:
        print(*found, sep="\n")
        return 1
    print("Layout float accumulation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
