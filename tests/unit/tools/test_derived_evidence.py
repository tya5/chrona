from __future__ import annotations

import json
from pathlib import Path
import subprocess

import yaml
import pytest

from tools.check_scene_perceptibility import committed_scene_paths, evaluate_committed_scenes as perceptibility
from tools.derived_evidence import (
    derived_paths, materializer_outputs, scene_paths, validate_materializers_present,
    validate_no_orphan_materializers,
)
import tools.derived_evidence as evidence
from tools.presentation_contrast import evaluate_committed_scenes as contrast
from tools.presentation_font_identity import evaluate_committed_scenes as font_identity


def _manifest(root):
    example = root / "examples/new-corpus"
    example.mkdir(parents=True)
    (example / "manifest.yaml").write_text(yaml.safe_dump({
        "version": "chrona/example-materializer/v0.1",
        "slides": [{"id": "new-slide", "expectedSvg": "generated/new.svg",
                    "expectedScene": "generated/new.scene.json", "context": "new-context.yaml"}],
    }), encoding="utf-8")
    (example / "new-context.yaml").write_text("id: new-context\n", encoding="utf-8")
    return example / "generated/new.scene.json"


def test_inventory_is_stable_and_matches_tracked_public_materializers():
    outputs = materializer_outputs()
    assert outputs == tuple(sorted(outputs))
    assert scene_paths() == tuple(sorted(scene_paths()))
    # A PR never authors declared evidence (the snapshot writes it into the work tree), so a
    # slide a PR adds is untracked until the main sync commits it: count untracked, unignored files.
    # Likewise a slide a PR removes keeps its tracked outputs until that sync retires them; the snapshot
    # deletes them from the work tree, so count only files that are present.
    tracked = subprocess.run(
        ("git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "examples"),
        check=True, capture_output=True,
    ).stdout.split(b"\0")
    tracked_outputs = tuple(sorted(
        path.decode() for path in tracked
        if path.endswith((b".svg", b".scene.json")) and Path(path.decode()).is_file()
    ))
    assert tuple(sorted(path.relative_to(Path.cwd()).as_posix()
                         for path in outputs)) == tracked_outputs
    # Counted from the raw manifests, not from `derived_paths` itself: one SVG per slide, a Scene where declared, the reports.
    slides = [slide for path in sorted(Path("examples").glob("*/manifest.yaml"))
              for slide in yaml.safe_load(path.read_bytes())["slides"]]
    declared = len(slides) + sum(1 for slide in slides if slide.get("expectedScene"))
    assert len(derived_paths()) == declared + len(evidence.REPORTS)


def test_new_unindexed_manifest_scene_is_inspected_and_missing_output_fails(tmp_path):
    scene = _manifest(tmp_path)
    discovered = committed_scene_paths(tmp_path)
    assert discovered == (scene.resolve(),)

    checks = (
        lambda: perceptibility(discovered, root=tmp_path),
        lambda: contrast(discovered, root=tmp_path),
        lambda: font_identity(discovered, root=tmp_path),
    )
    for check in checks:
        records = check()
        assert records
        assert records[0]["scene"] == "examples/new-corpus/generated/new.scene.json"
        assert records[0]["finding" if "finding" in records[0] else "code"]

    with pytest.raises(ValueError, match="E_DERIVED_EVIDENCE_MISSING_OUTPUT"):
        validate_materializers_present(tmp_path)

    scene.parent.mkdir(parents=True)
    scene.write_text(json.dumps({"surfaces": []}), encoding="utf-8")
    assert committed_scene_paths(tmp_path) == (scene.resolve(),)


def test_undeclared_generated_scene_is_rejected(tmp_path):
    _manifest(tmp_path)
    orphan = tmp_path / "examples/new-corpus/generated/retired.scene.json"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="E_DERIVED_EVIDENCE_UNDECLARED_OUTPUT"):
        validate_no_orphan_materializers(tmp_path)


def test_duplicate_slide_ids_are_rejected_before_target_lookup(tmp_path):
    example = tmp_path / "examples/new-corpus"
    example.mkdir(parents=True)
    slides = [{"id": "same", "expectedSvg": f"generated/{index}.svg"}
              for index in range(2)]
    (example / "manifest.yaml").write_text(yaml.safe_dump({"slides": slides}), encoding="utf-8")
    with pytest.raises(ValueError, match="E_DERIVED_EVIDENCE_MANIFEST"):
        materializer_outputs(tmp_path)


def test_staged_write_then_check_is_idempotent(tmp_path, monkeypatch):
    output = tmp_path / "docs/report.md"
    monkeypatch.setattr(evidence, "derived_paths", lambda root: (root / "docs/report.md",))
    monkeypatch.setattr(evidence, "validate_no_orphan_materializers", lambda root: None)
    monkeypatch.setattr(evidence, "validate_materializers_present", lambda root: None)

    def generate(root, *, write, jobs):
        path = root / "docs/report.md"
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("deterministic\n", encoding="utf-8")
        else:
            assert path.read_text(encoding="utf-8") == "deterministic\n"

    monkeypatch.setattr(evidence, "_generate", generate)
    assert evidence.main(("--write", "--root", str(tmp_path))) == 0
    first = output.read_bytes()
    assert evidence.main(("--write", "--root", str(tmp_path))) == 0
    assert output.read_bytes() == first
    assert evidence.main(("--check", "--root", str(tmp_path))) == 0


def test_generator_error_does_not_publish_staged_bytes(tmp_path, monkeypatch):
    output = tmp_path / "docs/report.md"
    output.parent.mkdir()
    output.write_text("prior\n", encoding="utf-8")
    monkeypatch.setattr(evidence, "derived_paths", lambda root: (root / "docs/report.md",))
    monkeypatch.setattr(evidence, "validate_no_orphan_materializers", lambda root: None)

    def fail(root, *, write, jobs):
        (root / "docs/report.md").write_text("incomplete\n", encoding="utf-8")
        raise RuntimeError("generation failed")

    monkeypatch.setattr(evidence, "_generate", fail)
    with pytest.raises(RuntimeError, match="generation failed"):
        evidence.main(("--write", "--root", str(tmp_path)))
    assert output.read_text(encoding="utf-8") == "prior\n"
