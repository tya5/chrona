from __future__ import annotations

from pathlib import Path
import shutil

import yaml

from chrona.usecases.deck_context import SelectedDeckContext
from tests.support.public_evidence import declared_slides
from tools.check_design_purity import _batch as design_purity
from tools.check_example_reachability import closure
from tools.check_theme_role_consumers import _closures
from tools.corpus_coverage import discover as corpus_discover
from tools.derived_evidence import scene_contexts, selected_contexts
from tools.example_inventory import _context, corpus
from tools.presentation_coverage import discover as presentation_discover
from tools.presentation_font_identity import _manifest_contexts


ROOT = Path(__file__).resolve().parents[3]


def _shared_example(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    examples = repo / "examples"
    example = examples / "aster-ssd"
    shutil.copytree(ROOT / "tests/fixtures/aster-ssd", example)
    authored = yaml.safe_load((example / "contexts/01-overview.yaml").read_bytes())
    manifest = {
        "version": "chrona/example-materializer/v0.1",
        "id": "aster-ssd",
        "role": "regression-corpus",
        "contextDefaults": authored["body"],
        "slides": [{
            "id": "overview",
            "evidence": "Shared presentation with one slide override source.",
            "contextOverrides": {"id": authored["id"]},
            "expectedSvg": "generated/overview.svg",
            "expectedScene": "generated/overview.scene.json",
        }],
    }
    manifest_path = example / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return repo, manifest_path


def test_inspection_consumers_use_the_same_composed_context_without_a_staged_file(tmp_path):
    root, manifest_path = _shared_example(tmp_path)
    example = manifest_path.parent

    selected_pairs = selected_contexts(root)
    assert len(selected_pairs) == 1
    source = selected_pairs[0][1]
    assert isinstance(source, SelectedDeckContext)
    assert source.source_mode == "composed"
    assert source.source_path is None
    assert source.document["body"] == yaml.safe_load(
        (ROOT / "tests/fixtures/aster-ssd/contexts/01-overview.yaml").read_bytes())["body"]
    assert not (example / source.address).exists()

    slide = declared_slides(root)[0]
    assert slide.context == source
    assert scene_contexts(root)[slide.scene] == source
    assert _manifest_contexts(root)[slide.scene] == source

    inventory_entry = corpus(root)[("aster-ssd", "overview")]
    assert inventory_entry["context"] is None
    assert _context(root, inventory_entry)["body"] == source.document["body"]

    coverage_slide = presentation_discover(root)[0]
    assert coverage_slide.context_source == source
    project = corpus_discover(root)[0]
    assert project.identifier == "aster-ssd"

    reached, _edges = closure(root / "examples")
    assert (example / source.address).resolve() not in reached
    assert (example / "contexts/01-overview.yaml").resolve() not in reached

    context_closures = list(_closures(root))
    assert any(path == example / "themes/executive-light.yaml" for path, _docs in context_closures)
    design_purity(root / "examples")
