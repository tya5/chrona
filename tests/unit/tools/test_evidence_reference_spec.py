"""Spec 17 section 8 may say an evidence reference is opened or verified only if some code opens one (#769).

Owner decision (#769, option 2): `artifacts` and `acceptanceEvidence` references are shape-only records. chrona validates
their shape and does not open or verify the target. This test keeps the spec and the code saying the same thing:

* it finds every function in `src` that handles those fields (by the `resourceReference` type, the field names, the
  evidence kinds or the `IDP-EVIDENCE-` codes), and requires each one to be named in a registry below;
* it requires every registered shape-only function to contain no call that opens or reads anything;
* it requires the spec to match the registry: shape-only wording while `OPENING_FUNCTIONS` is empty, and no
  shape-only wording once a function is registered as opening an evidence target.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SPEC = ROOT / "docs/specification/17-implementation-delivery-profile.md"
SRC = ROOT / "src"

# "path/relative/to/repo.py:qualified.name" of functions that handle an evidence reference WITHOUT opening its target.
SHAPE_ONLY_FUNCTIONS = {"src/chrona/extensions/profiles.py:_validate_value"}
# Functions that open (read, resolve or verify) the target of an evidence reference. Add one here only together with the
# feature that consumes evidence, and change spec 17 section 8 in the same change (open through the shared Store
# address guard and verify `contentIdentity`).
OPENING_FUNCTIONS: set[str] = set()

MARKERS = ("resourceReference", "acceptanceEvidence", "delivery-artifact", "delivery-acceptance-evidence", "IDP-EVIDENCE-")
OPENING_CALLS = {"read", "read_bytes", "read_text", "open", "resolve", "verify", "fetch", "load", "safe_load"}
OPENING_PARAMETERS = {"reader", "store", "stores", "snapshot_reader"}

AFFIRMATIVE = (  # wording that says an evidence reference is opened, resolved or verified
    r"verified Revision Store resource reference", r"Store verifies", r"failed immutable verification",
    r"resolves to an immutable", r"rejected by that Store", r"identity/content mismatch",
)
SHAPE_ONLY = r"does not open, resolve, or verify\s+the target"


def _section_8() -> str:
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("## 8. ")
    return " ".join(text[start:].split())


def _handlers() -> dict[str, ast.AST]:
    found: dict[str, ast.AST] = {}
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()

        def visit(node: ast.AST, prefix: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    qualified = f"{prefix}{child.name}"
                    if not isinstance(child, ast.ClassDef) and any(
                        isinstance(n, ast.Constant) and isinstance(n.value, str) and any(m in n.value for m in MARKERS)
                        for n in ast.walk(child)
                    ):
                        found[f"{relative}:{qualified}"] = child
                    visit(child, f"{qualified}.")
                else:
                    visit(child, prefix)

        visit(tree, "")
    return found


def _opens_something(function: ast.AST) -> list[str]:
    assert isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
    reasons = [f"parameter {a.arg}" for a in function.args.args + function.args.kwonlyargs if a.arg in OPENING_PARAMETERS]
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in OPENING_CALLS:
                reasons.append(f"call {name}()")
    return sorted(set(reasons))


def test_every_function_that_handles_evidence_references_is_registered():
    handlers = set(_handlers())
    registered = SHAPE_ONLY_FUNCTIONS | OPENING_FUNCTIONS
    assert handlers == registered, (
        f"evidence-reference handlers changed: unregistered {sorted(handlers - registered)}, "
        f"stale {sorted(registered - handlers)}. Register a function that only checks shape in SHAPE_ONLY_FUNCTIONS; "
        "register one that opens, resolves or verifies a target in OPENING_FUNCTIONS and update spec 17 section 8 "
        "(see #769) in the same change."
    )


def test_shape_only_functions_do_not_open_anything():
    handlers = _handlers()
    for name in SHAPE_ONLY_FUNCTIONS:
        reasons = _opens_something(handlers[name])
        assert not reasons, (
            f"{name} is registered as shape-only but has {reasons}. If it now opens an evidence target, move it to "
            "OPENING_FUNCTIONS and update spec 17 section 8 (open through the shared Store address guard and verify "
            "`contentIdentity`); otherwise remove the call."
        )


def test_spec_17_says_what_the_code_does_with_evidence_references():
    section = _section_8()
    if OPENING_FUNCTIONS:
        assert not re.search(SHAPE_ONLY, section), (
            f"{sorted(OPENING_FUNCTIONS)} open an evidence reference but spec 17 section 8 still says chrona does not "
            "open or verify it: update the section (#769 revisit condition) together with this test."
        )
        return
    claims = [pattern for pattern in AFFIRMATIVE if re.search(pattern, section)]
    assert not claims, (
        f"spec 17 section 8 says an evidence reference is opened, resolved or verified ({claims}) but no code path opens "
        "one (OPENING_FUNCTIONS is empty). Reword the section to say chrona validates the reference's shape only "
        "(#769 owner decision), or implement the consumer and register it in OPENING_FUNCTIONS in the same change."
    )
    assert re.search(SHAPE_ONLY, section), (
        "spec 17 section 8 must state that chrona validates the evidence reference's shape and does not open, resolve, "
        "or verify the target while OPENING_FUNCTIONS is empty (#769)."
    )
