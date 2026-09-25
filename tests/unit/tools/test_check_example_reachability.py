from pathlib import Path

import pytest

from tools.check_example_reachability import ExampleReachabilityError, closure, reachable_view_paths, validate


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_public_examples_have_only_declared_or_reasoned_files():
    root = _root()
    validate(root)
    paths = {path.relative_to(root).as_posix() for path in reachable_view_paths(root)}
    assert "examples/aster-ssd/views/01-overview.yaml" in paths
    assert all("aster-ssd/views/0" not in path or path.endswith("01-overview.yaml") for path in paths)


def test_typed_local_context_reference_cannot_silently_point_at_a_missing_file(tmp_path):
    example = tmp_path / "examples/demo"
    (example / "contexts").mkdir(parents=True)
    (example / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\ncontext: contexts/one.yaml\nslides: [{id: one, expectedSvg: generated/one.svg}]\n",
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
        "version: chrona/example-materializer/v0.1\ncontext: context.yaml\nslides: [{id: one, expectedSvg: generated/one.svg}]\n",
        encoding="utf-8",
    )
    with pytest.raises(ExampleReachabilityError, match="E_EXAMPLE_REACHABILITY_MISSING"):
        closure(tmp_path / "examples")
