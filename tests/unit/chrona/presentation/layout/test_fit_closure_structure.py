"""Guard the current Layout path against reintroducing a fit refusal."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]


def test_production_layout_has_no_required_fit_refusal_site():
    layout = ROOT / "src/chrona/presentation/layout"
    offenders = [path.relative_to(ROOT).as_posix() for path in layout.rglob("*.py")
                 if "E_LAYOUT_REQUIRED_OVERFLOW" in path.read_text(encoding="utf-8")]
    assert offenders == []


def test_render_use_case_does_not_suggest_rematerialization_for_fit_shortage():
    source = (ROOT / "src/chrona/usecases/render_review.py").read_text(encoding="utf-8")
    assert "E_LAYOUT_REQUIRED_OVERFLOW" not in source
    assert "set environment.viewport.blockSize" not in source
