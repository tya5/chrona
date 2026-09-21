from hashlib import sha256
from pathlib import Path

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
        try:
            materialize(manifest, "executive", tmp_path / "controller", write=False)
        except ValueError as error:
            assert str(error) == "E_MATERIALIZER_MISMATCH"
        else:
            raise AssertionError("expected mismatch")
    finally:
        expected.write_bytes(original)


def test_materializer_derives_strict_identities_for_copied_closure(tmp_path):
    example = ROOT / "examples/aster-ssd"
    context_path = example / "contexts/01-overview.yaml"
    snapshot = tmp_path / "snapshot"; snapshot.mkdir()

    reference, revision = _copy_context_closure(example, context_path, snapshot)

    derived = yaml.safe_load((snapshot / revision / "contexts/01-overview.yaml").read_text())
    references = [derived["body"][name] for name in ("project", "view", "theme", "colorScheme", "layout")]
    references.extend(derived["body"]["inputs"].values())
    for item in references:
        payload = (example / item["address"]).read_bytes()
        assert item["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
    assert reference["contentIdentity"] == "sha256:" + sha256((snapshot / revision / "contexts/01-overview.yaml").read_bytes()).hexdigest()


def test_materializer_uses_each_declared_halcyon_slide_context(tmp_path):
    example = ROOT / "examples/halcyon-1"
    for index, relative in enumerate((
        "contexts/01-mission-brief.yaml",
        "contexts/02-programme-board.yaml",
        "contexts/03-launch-campaign.yaml",
    )):
        snapshot = tmp_path / str(index); snapshot.mkdir()
        reference, revision = _copy_context_closure(example, example / relative, snapshot)
        assert reference["id"] == yaml.safe_load((snapshot / revision / relative).read_text())["id"]
