"""Unit suites use deterministic work counts; the CLI owns its runtime budget."""
import ast
from pathlib import Path

from tools import schema_equivalence as gate


ROOT = Path(__file__).resolve().parents[3]
UNIT_TESTS = ROOT / "tests" / "unit"
WALLCLOCK_BENCHMARK_ALLOWLIST: frozenset[str] = frozenset()


def test_cli_runtime_guard_is_opt_out_only_for_semantic_callers(monkeypatch):
    clock = iter((0.0, 61.0))
    monkeypatch.setattr(gate.time, "monotonic", lambda: next(clock))
    guarded = gate.run_gate(ROOT, layers=("L2",), documents={})

    clock = iter((0.0, 61.0))
    monkeypatch.setattr(gate.time, "monotonic", lambda: next(clock))
    semantic = gate.run_gate(ROOT, layers=("L2",), documents={}, enforce_runtime_budget=False)

    runtime_failures = [failure for failure in guarded.failures if failure.startswith("runtime:")]
    assert runtime_failures == ["runtime: L2+L3 took 61.0s, over the 60s budget"]
    assert not any(failure.startswith("runtime:") for failure in semantic.failures)
    assert {failure for failure in guarded.failures if not failure.startswith("runtime:")} == set(semantic.failures)


def _assert_wallclock_references(node: ast.AST) -> set[str]:
    references = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in {"elapsed", "RUNTIME_BUDGET_SECONDS"}:
            references.add(child.id)
        elif isinstance(child, ast.Attribute) and child.attr in {"timings", "monotonic", "perf_counter"}:
            references.add(child.attr)
    return references


def test_unit_tests_have_no_wallclock_assertions_outside_benchmark_allowlist():
    violations = []
    for path in sorted(UNIT_TESTS.rglob("test_*.py")):
        relative = path.relative_to(ROOT).as_posix()
        if relative in WALLCLOCK_BENCHMARK_ALLOWLIST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                refs = _assert_wallclock_references(node)
                if refs:
                    violations.append(f"{relative}:{node.lineno}: {', '.join(sorted(refs))}")
    assert not violations, "wall-clock unit assertions: " + "; ".join(violations)

