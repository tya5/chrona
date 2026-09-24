from pathlib import Path

from tools.render_design_gallery import render


def test_gallery_pages_are_deterministic_and_documentary():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())

    pages = render(root)

    assert pages == render(root)
    page = pages[Path("docs/gallery/sets/controller-z-executive-status.md")]
    assert "Presentation-reference diff" in page
    assert "Referenced-resource YAML diff" in page
    assert "tools/render_design_gallery.py --root ." in page
    assert "project.yaml" not in page
    assert "presentation-coverage.md" in pages[Path("docs/gallery/README.md")]
