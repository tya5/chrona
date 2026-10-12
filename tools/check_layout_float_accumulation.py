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
    "engine.py": frozenset({"_allocate", "_resolve_flexible_tracks", "_measure_node", "_linear", "_grid", "_flow", "block"}),
    "sources.py": frozenset({"measure_sources"}),
}


DECIMAL_SEEDED_SUM_FUNCTIONS = {
    "presentation.py": frozenset({"_bounded_column_widths"}),
    "surface_base.py": frozenset({"prepare_surface_inline"}),
    "table_measurement.py": frozenset({"measure_bounded_table"}),
    "tracks.py": frozenset({"resolve_flexible_tracks"}),
    # Extracted source factory preserves the previous Application precision:
    # every visual advance is Decimal(str(width + gap)), seeded by Decimal(0).
    "surface_source_inputs.py": frozenset({"_annotation_source_input"}),
}


def _decimal_zero(node: ast.expr) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "Decimal" and not node.keywords and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0)


class _Sums(ast.NodeVisitor):
    def __init__(self, file_name: str, decimal_zeros: frozenset[str] = frozenset()) -> None:
        self.file_name = file_name
        self.decimal_zeros = decimal_zeros
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
        if (self.function in DECIMAL_SEEDED_SUM_FUNCTIONS.get(self.file_name, frozenset())
                and len(node.args) == 2 and not node.keywords):
            seed = node.args[1]
            return _decimal_zero(seed) or (isinstance(seed, ast.Name) and seed.id in self.decimal_zeros)
        if len(node.args) != 1 or node.keywords:
            return False
        value = node.args[0]
        # Builtin len returns an integer. With sum's implicit integer seed,
        # these are logical record counts, not accumulated float geometry.
        if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id == "map" and len(value.args) == 2 and not value.keywords
                and isinstance(value.args[0], ast.Name) and value.args[0].id == "len"):
            return True
        if not isinstance(value, ast.GeneratorExp):
            return False
        term = value.elt
        return (isinstance(term, (ast.Compare, ast.BoolOp, ast.UnaryOp))
                or (isinstance(term, ast.Call) and isinstance(term.func, ast.Name)
                    and term.func.id == "len" and len(term.args) == 1 and not term.keywords))


def violations(root: Path = LAYOUT) -> tuple[str, ...]:
    """Return stable failures for direct builtin sums outside reviewed classes."""
    found: list[str] = []
    for path in sorted(root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        decimal_zeros = frozenset(target.id for node in tree.body
                                 if isinstance(node, ast.Assign) and _decimal_zero(node.value)
                                 for target in node.targets if isinstance(target, ast.Name))
        visitor = _Sums(path.name, decimal_zeros)
        visitor.visit(tree)
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
