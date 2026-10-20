from pathlib import Path
import shutil
import sys

import pytest
import yaml

from tools import render_design_gallery
from tools.render_design_gallery import render
from tools.render_design_gallery import _single_resource_diff


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


def test_composed_gallery_source_links_to_manifest_and_names_slide(tmp_path):
    root = tmp_path
    example = root / "examples/demo"
    fixtures = Path(__file__).resolve().parents[2] / "fixtures/aster-ssd"
    shutil.copytree(fixtures, example)
    context = yaml.safe_load((example / "contexts/01-overview.yaml").read_bytes())
    alternate = yaml.safe_load((example / "views/01-overview.yaml").read_bytes())
    alternate["id"] = "alternate-view"
    (example / "views/alternate-view.yaml").write_text(yaml.safe_dump(alternate, sort_keys=False), encoding="utf-8")
    (example / "generated/alternate.svg").write_bytes((example / "generated/overview.svg").read_bytes())
    body = context["body"]
    alternate_view = dict(body["view"], id="alternate-view", address="views/alternate-view.yaml")
    (example / "manifest.yaml").write_text(yaml.safe_dump({
        "version": "chrona/example-materializer/v0.1", "id": "demo", "role": "regression-corpus",
        "contextDefaults": body,
        "slides": [
            {"id": "overview", "evidence": "overview", "expectedSvg": "generated/overview.svg",
             "contextOverrides": {"id": "overview-context"}},
            {"id": "alternate", "evidence": "alternate", "expectedSvg": "generated/alternate.svg",
             "contextOverrides": {"id": "alternate-context", "body": {"view": alternate_view}}},
        ],
    }, sort_keys=False), encoding="utf-8")
    (root / "docs/gallery").mkdir(parents=True)
    (root / "docs/gallery/example-gallery.yaml").write_text(yaml.safe_dump({
        "version": "chrona/design-gallery/v0.2", "entries": [
            {"id": "left", "corpus": "demo", "slide": "overview",
             "narrative": {"title": "Overview", "audience": "A", "purpose": "Compare"},
             "comparison": {"set": "pair", "axis": "View selection", "dimension": "content"},
             "target": body["target"], "accessibility": {"note": "Text"}},
            {"id": "right", "corpus": "demo", "slide": "alternate",
             "narrative": {"title": "Alternate", "audience": "A", "purpose": "Compare"},
             "comparison": {"set": "pair", "axis": "View selection", "dimension": "content"},
             "target": body["target"], "accessibility": {"note": "Text"}},
        ],
    }, sort_keys=False), encoding="utf-8")

    pages = render(root)
    page = pages[Path("docs/gallery/sets/pair.md")]

    assert "[Manifest (slide `overview`)](../../../examples/demo/manifest.yaml)" in page
    assert "[Manifest (slide `alternate`)](../../../examples/demo/manifest.yaml)" in page
    assert "_deck-contexts" not in page


def test_resource_diff_reads_package_store_references(tmp_path):
    base = Path("examples/demo")
    example = tmp_path / base
    example.mkdir(parents=True)
    (example / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nid: demo\nrole: regression-corpus\nstores: []\nslides: []\n",
        encoding="utf-8",
    )
    stable = {"id": "stable", "address": "unused.yaml", "revision": {"token": "r1"},
              "store": {"provider": "local", "identity": "demo"}}
    contexts = []
    for identifier in ("yuya", "target-b"):
        view = {"id": identifier, "address": f"designs/{identifier}/theme.yaml",
                "revision": {"token": "r1"}, "store": {"provider": "package", "identity": "chrona.resources"}}
        contexts.append({"body": {"view": stable, "theme": view, "colorScheme": stable, "layout": stable}})

    result = _single_resource_diff(tmp_path, [base, base], contexts)

    assert any("Referenced-resource YAML diff" in line for line in result)
    assert any(line.startswith("-") and line.endswith("id: yuya") for line in result)
    assert any(line.startswith("+") and line.endswith("id: target-b") for line in result)
