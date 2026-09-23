from pathlib import Path

import pytest

from tools.example_inventory import ExampleInventoryError, validate


def _root(tmp_path: Path) -> Path:
    (tmp_path / "examples/demo").mkdir(parents=True)
    (tmp_path / "docs/guides").mkdir(parents=True)
    (tmp_path / "docs/gallery").mkdir(parents=True)
    (tmp_path / "examples/demo/manifest.yaml").write_text("id: demo\nrole: regression-corpus\nslides: [{id: overview, evidence: Overview}]\n")
    (tmp_path / "docs/guides/example-curriculum.yaml").write_text("version: chrona/example-catalog/v0.1\nentries: [{corpus: demo, slide: overview}]\n")
    (tmp_path / "docs/gallery/example-gallery.yaml").write_text("version: chrona/example-catalog/v0.1\nentries: [{corpus: demo, slide: overview}]\n")
    return tmp_path


def test_inventory_accepts_declared_corpus_references(tmp_path):
    assert validate(_root(tmp_path)) == (1, 1, 1)


def test_inventory_rejects_dangling_catalog_reference(tmp_path):
    root = _root(tmp_path)
    (root / "docs/gallery/example-gallery.yaml").write_text("version: chrona/example-catalog/v0.1\nentries: [{corpus: demo, slide: absent}]\n")
    with pytest.raises(ExampleInventoryError, match="E_EXAMPLE_CATALOG_REFERENCE"):
        validate(root)
