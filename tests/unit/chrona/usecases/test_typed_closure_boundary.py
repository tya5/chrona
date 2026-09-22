from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def test_render_use_case_has_no_generic_closure_kind_lookup():
    source = (ROOT / "src/chrona/usecases/render_review.py").read_text(encoding="utf-8")
    forbidden = ("class _Closure", ".resource(", "def get(self, kind", "def all_of(self, kind", "ClosureResource")
    assert all(fragment not in source for fragment in forbidden)
