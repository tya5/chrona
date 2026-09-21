from hashlib import sha256
from pathlib import Path
import shutil

import pytest
import yaml

from tools.materialize_example import _copy_context_closure, materialize


ROOT = Path(__file__).resolve().parents[2]


def test_declared_examples_reproduce_by_public_cli(tmp_path):
    materialize(ROOT / "examples/controller-z/manifest.yaml", "executive", tmp_path / "controller", write=False)
    materialize(ROOT / "examples/aster-ssd/manifest.yaml", "overview", tmp_path / "aster", write=False)


def test_materializer_detects_changed_expected_svg(tmp_path):
    manifest = ROOT / "examples/controller-z/manifest.yaml"
    expected = ROOT / "examples/controller-z/generated/executive.svg"
    original = expected.read_bytes()
    try:
        expected.write_bytes(original + b"changed")
        with pytest.raises(ValueError, match="E_MATERIALIZER_MISMATCH"):
            materialize(manifest, "executive", tmp_path / "controller", write=False)
    finally:
        expected.write_bytes(original)


def test_materializer_preserves_authored_context_bytes_and_pins(tmp_path):
    example = ROOT / "examples/aster-ssd"
    context_path = example / "contexts/01-overview.yaml"
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()

    reference, revision = _copy_context_closure(example, context_path, snapshot)

    copied = snapshot / revision / "contexts/01-overview.yaml"
    assert copied.read_bytes() == context_path.read_bytes()
    assert reference["contentIdentity"] == "sha256:" + sha256(context_path.read_bytes()).hexdigest()
    assert yaml.safe_load(copied.read_text()) == yaml.safe_load(context_path.read_text())


def test_materializer_rejects_an_authored_stale_pin_before_write(tmp_path):
    copied_example = tmp_path / "halcyon"
    shutil.copytree(ROOT / "examples/halcyon-1", copied_example)
    context = copied_example / "contexts/01-mission-brief.yaml"
    raw = context.read_text()
    context.write_text(raw.replace("sha256:21672446b8bb2813efa90550b056379828d194e8dd4601397ab6b2f9fba7909e", "sha256:" + "0" * 64))
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY"):
        materialize(copied_example / "manifest.yaml", "mission-brief", tmp_path / "out", write=True)


def test_materializer_uses_each_declared_halcyon_slide_context(tmp_path):
    example = ROOT / "examples/halcyon-1"
    for index, relative in enumerate((
        "contexts/01-mission-brief.yaml",
        "contexts/02-programme-board.yaml",
        "contexts/03-launch-campaign.yaml",
    )):
        snapshot = tmp_path / str(index)
        snapshot.mkdir()
        reference, revision = _copy_context_closure(example, example / relative, snapshot)
        assert reference["id"] == yaml.safe_load((snapshot / revision / relative).read_text())["id"]
