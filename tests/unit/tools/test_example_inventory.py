from pathlib import Path

import pytest

from tools.example_inventory import ExampleInventoryError, validate


def _root(tmp_path: Path) -> Path:
    (tmp_path / "examples/demo").mkdir(parents=True)
    (tmp_path / "docs/guides").mkdir(parents=True)
    (tmp_path / "docs/gallery").mkdir(parents=True)
    (tmp_path / "examples/demo/contexts").mkdir()
    (tmp_path / "examples/demo/manifest.yaml").write_text("id: demo\nrole: regression-corpus\ncontext: contexts/one.yaml\nslides: [{id: overview, evidence: Overview, expectedSvg: generated/one.svg}, {id: alternative, evidence: Alternative, context: contexts/two.yaml, expectedSvg: generated/two.svg}]\n")
    (tmp_path / "examples/demo/contexts/one.yaml").write_text("kind: render-context\nbody:\n  project: {id: project}\n  view: {id: view}\n  theme: {id: theme}\n  colorScheme: {id: scheme}\n  layout: {id: layout}\n  inputs: {}\n  target: {kind: svg, capabilities: []}\n")
    (tmp_path / "examples/demo/contexts/two.yaml").write_text("kind: render-context\nbody:\n  project: {id: project}\n  view: {id: alternate}\n  theme: {id: theme}\n  colorScheme: {id: scheme}\n  layout: {id: layout}\n  inputs: {}\n  target: {kind: svg, capabilities: []}\n")
    (tmp_path / "docs/guides/example-curriculum.yaml").write_text("version: chrona/example-catalog/v0.1\nentries: [{corpus: demo, slide: overview}]\n")
    (tmp_path / "docs/gallery/example-gallery.yaml").write_text("version: chrona/design-gallery/v0.1\nentries:\n  - {id: one, corpus: demo, slide: overview, narrative: {title: One, audience: A, purpose: P}, comparison: {set: pair, axis: focus}, target: {kind: svg, capabilities: []}, accessibility: {note: Text}}\n  - {id: two, corpus: demo, slide: alternative, narrative: {title: Two, audience: A, purpose: P}, comparison: {set: pair, axis: focus}, target: {kind: svg, capabilities: []}, accessibility: {note: Text}}\n")
    return tmp_path


def test_inventory_accepts_declared_corpus_references(tmp_path):
    assert validate(_root(tmp_path)) == (2, 1, 2)


def test_inventory_rejects_dangling_catalog_reference(tmp_path):
    root = _root(tmp_path)
    (root / "docs/gallery/example-gallery.yaml").write_text("version: chrona/design-gallery/v0.1\nentries: [{id: absent, corpus: demo, slide: absent, narrative: {title: A, audience: A, purpose: P}, comparison: {set: pair, axis: focus}, target: {kind: svg, capabilities: []}, accessibility: {note: Text}}]\n")
    with pytest.raises(ExampleInventoryError, match="E_DESIGN_GALLERY_REFERENCE"):
        validate(root)
