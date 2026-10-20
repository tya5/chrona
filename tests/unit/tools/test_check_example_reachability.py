from pathlib import Path
import shutil

import pytest
import yaml

from tools.check_example_reachability import ExampleReachabilityError, closure, reachable_view_paths, validate


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_public_examples_have_only_declared_or_reasoned_files():
    root = _root()
    validate(root)
    paths = {path.relative_to(root).as_posix() for path in reachable_view_paths(root)}
    assert "examples/halcyon-1/views/02-programme-board.yaml" in paths
    frozen, _ = closure(root / "tests/fixtures")
    assert root / "tests/fixtures/aster-ssd/views/01-overview.yaml" in frozen


def test_typed_local_context_reference_cannot_silently_point_at_a_missing_file(tmp_path):
    example = tmp_path / "examples/demo"
    (example / "contexts").mkdir(parents=True)
    (example / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nrole: regression-corpus\ncontext: contexts/one.yaml\n"
        "slides: [{id: one, evidence: one, expectedSvg: generated/one.svg}]\n",
        encoding="utf-8",
    )
    (example / "contexts/one.yaml").write_text(
        "body:\n  project: {store: {provider: local}, address: project.yaml}\n",
        encoding="utf-8",
    )
    with pytest.raises(ExampleReachabilityError, match="E_EXAMPLE_REACHABILITY_MISSING"):
        closure(tmp_path / "examples")


def test_manifest_evidence_cannot_name_a_missing_generated_file(tmp_path):
    example = tmp_path / "examples/demo"
    example.mkdir(parents=True)
    (example / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nrole: regression-corpus\ncontext: context.yaml\n"
        "slides: [{id: one, evidence: one, expectedSvg: generated/one.svg}]\n",
        encoding="utf-8",
    )
    with pytest.raises(ExampleReachabilityError, match="E_EXAMPLE_REACHABILITY_MISSING"):
        closure(tmp_path / "examples")


def test_composed_context_references_are_reachable_without_a_fake_context_file(tmp_path):
    example = tmp_path / "examples/demo"
    shutil.copytree(_root() / "tests/fixtures/aster-ssd", example)
    authored = yaml.safe_load((example / "contexts/01-overview.yaml").read_bytes())
    (example / "manifest.yaml").write_text(yaml.safe_dump({
        "version": "chrona/example-materializer/v0.1", "id": "demo", "role": "regression-corpus",
        "contextDefaults": authored["body"],
        "slides": [{"id": "overview", "evidence": "shared", "expectedSvg": "generated/overview.svg",
                    "expectedScene": "generated/overview.scene.json",
                    "contextOverrides": {"id": authored["id"]}}],
    }, sort_keys=False), encoding="utf-8")

    reached, edges = closure(tmp_path / "examples")

    assert (example / "manifest.yaml").resolve() in reached
    assert (example / "project.yaml").resolve() in reached
    assert (example / "views/01-overview.yaml").resolve() in reached
    assert (example / "contexts/01-overview.yaml").resolve() not in reached
    assert (example / "_deck-contexts/demo/overview.yaml").resolve() not in reached
    assert (example / "project.yaml").resolve() in edges[(example / "manifest.yaml").resolve()]
