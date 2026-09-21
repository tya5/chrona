from pathlib import Path

from tools.materialize_example import materialize


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
