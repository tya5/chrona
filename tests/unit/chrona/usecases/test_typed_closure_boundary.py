import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _has_generic_contract_access(source: str) -> bool:
    """Match forbidden contract accessors, not longer ingress names containing them."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if node.attr in {"document", "facts"}:
            return True
        if (node.attr == "body" and (
                isinstance(node.value, ast.Name) and node.value.id == "context"
                or isinstance(node.value, ast.Attribute) and node.value.attr == "context")):
            return True
    return False


def test_render_use_case_has_no_generic_closure_kind_lookup():
    source = (ROOT / "src/chrona/usecases/render_review.py").read_text(encoding="utf-8")
    forbidden = ("class _Closure", ".resource(", "def get(self, kind", "def all_of(self, kind", "ClosureResource")
    assert all(fragment not in source for fragment in forbidden)


def test_production_closure_consumers_do_not_expose_generic_contract_documents():
    sources = [
        ROOT / "src/chrona/presentation/model/closure.py",
        ROOT / "src/chrona/usecases/render_review.py",
        ROOT / "src/chrona/app/cli.py",
    ]
    assert all(not _has_generic_contract_access(path.read_text(encoding="utf-8")) for path in sources)


def test_generic_contract_access_guard_matches_exact_attributes_not_ingress_names():
    assert _has_generic_contract_access("value.document")
    assert _has_generic_contract_access("value.facts")
    assert _has_generic_contract_access("context.body")
    assert _has_generic_contract_access("render.context.body")
    assert not _has_generic_contract_access("preset_members.documents_by_path")
    assert not _has_generic_contract_access("resources_by_path[declaration['path']]")
    assert not _has_generic_contract_access("'context.body in documentation'")
