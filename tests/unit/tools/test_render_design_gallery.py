from pathlib import Path
import sys

import pytest

from tools import render_design_gallery
from tools.render_design_gallery import render


def test_gallery_pages_are_deterministic_and_documentary():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())

    pages = render(root)

    assert pages == render(root)
    page = pages[Path("docs/gallery/sets/halcyon-investigating-slip.md")]
    assert "Presentation-reference diff" in page
    assert "Referenced-resource YAML diff" in page
    assert "tools/render_design_gallery.py --root ." in page
    assert "project.yaml" not in page
    assert "presentation-coverage.md" in pages[Path("docs/gallery/README.md")]


def test_check_fails_when_a_generated_gallery_page_is_stale(tmp_path, monkeypatch):
    page = Path("docs/gallery/README.md")
    target = tmp_path / page
    target.parent.mkdir(parents=True)
    target.write_text("stale\n", encoding="utf-8")
    monkeypatch.setattr(render_design_gallery, "render", lambda _root: {page: "fresh\n"})
    monkeypatch.setattr(sys, "argv", ["render_design_gallery.py", "--root", str(tmp_path), "--check"])

    with pytest.raises(SystemExit, match="E_DESIGN_GALLERY_STALE"):
        render_design_gallery.main()
