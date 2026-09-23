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
    manifest = ROOT / "examples/halcyon-1/manifest.yaml"
    for slide in yaml.safe_load(manifest.read_text())["slides"]:
        materialize(manifest, slide["id"], tmp_path / slide["id"], write=False)


def test_controller_executive_public_evidence_exercises_inside_and_fallback_labels(tmp_path):
    materialize(ROOT / "examples/controller-z/manifest.yaml", "executive", tmp_path / "controller", write=False)
    artifact = (tmp_path / "controller/review.svg").read_text()
    assert 'data-scene-id="member-label:firmware:firmware"' in artifact
    assert 'data-scene-id="member-label:firmware:firmware" data-source-ref="firmware" data-purpose="member-label" x="784.375" y="253.625" font-family="Nimbus Sans, Arial, sans-serif" font-weight="400" font-size="14" fill="#000000"' in artifact
    assert 'data-scene-id="member-label:evb-arrival:evb-arrival" data-source-ref="evb-arrival" data-purpose="member-label" x="1047.416" y="409.325" font-family="Nimbus Sans, Arial, sans-serif" font-weight="400" font-size="14" fill="#172033"' in artifact


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
    value = yaml.safe_load(context.read_text())
    value["body"]["inputs"]["actual"]["contentIdentity"] = "sha256:" + "0" * 64
    context.write_text(yaml.safe_dump(value, sort_keys=False))
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY"):
        materialize(copied_example / "manifest.yaml", "mission-brief", tmp_path / "out", write=True)

def test_materializer_uses_each_declared_halcyon_slide_context(tmp_path):
    example = ROOT / "examples/halcyon-1"
    manifest = yaml.safe_load((example / "manifest.yaml").read_text())
    for index, slide in enumerate(manifest["slides"]):
        relative = slide.get("context", manifest["context"])
        snapshot = tmp_path / str(index)
        snapshot.mkdir()
        reference, revision = _copy_context_closure(example, example / relative, snapshot)
        assert reference["id"] == yaml.safe_load((snapshot / revision / relative).read_text())["id"]


def test_flight_readiness_public_artifact_exercises_advanced_contracts(tmp_path):
    example = ROOT / "examples/halcyon-1"
    materialize(example / "manifest.yaml", "flight-readiness", tmp_path / "flight-readiness", write=False)
    artifact = (tmp_path / "flight-readiness/review.svg").read_text()
    evidence = yaml.safe_load((tmp_path / "flight-readiness/closure.yaml").read_text())
    assert evidence["scenarios"][0]["scenarioId"] == "tvac-slip"
    assert '<a href="https://example.test/halcyon-1/reviews/frr"' in artifact
    # Only launch→LEOP is driving; its four current/scenario comparison facets
    # remain visible. Endpoint-critical neighbours must not become a critical chain.
    assert artifact.count('marker-end="url(#marker-dependency-critical-triangle)"') == 4
    for object_id, wbs in (("mission-closeout", "6"), ("frr", "6.1"), ("launch", "6.2"), ("leop", "6.3"), ("first-light", "6.4")):
        assert f'data-scene-id="cell:{object_id}:WBS"' in artifact
        assert f'>{wbs}</text>' in artifact
    assert artifact.count('data-scene-id="cell:frr:Float"') == 1


def test_materializer_rejects_a_supplied_wrong_font_pin_without_writing_svg(tmp_path):
    copied_example = tmp_path / "halcyon-font"
    shutil.copytree(ROOT / "examples/halcyon-1", copied_example)
    context = copied_example / "contexts/02-programme-board.yaml"
    value = yaml.safe_load(context.read_text())
    value["body"]["environment"]["fontMetrics"]["assets"][0]["contentIdentity"] = "sha256:" + "0" * 64
    context.write_text(yaml.safe_dump(value, sort_keys=False))
    expected = copied_example / "generated/02-programme-board.svg"
    original = expected.read_bytes()
    with pytest.raises(ValueError, match="E_MATERIALIZER_FONT_IDENTITY"):
        materialize(copied_example / "manifest.yaml", "programme-board", tmp_path / "out-font", write=True)
    assert expected.read_bytes() == original


def test_materializer_records_selected_scenario_evidence_and_omits_unselected_scenarios(tmp_path):
    example = ROOT / "examples/halcyon-1"
    manifest = example / "manifest.yaml"
    materialize(manifest, "tvac-slip", tmp_path / "scenario", write=False)
    evidence = yaml.safe_load((tmp_path / "scenario/closure.yaml").read_text())
    assert evidence["scenarios"][0]["scenarioId"] == "tvac-slip"
    assert evidence["scenarios"][0]["title"] == "System TVAC slips one week"
    assert evidence["scenarios"][0]["contentIdentity"].startswith("sha256:")
    assert "data-purpose=\"snapshot\"" in (tmp_path / "scenario/review.svg").read_text()
    assert "System TVAC slips one week" in (tmp_path / "scenario/review.svg").read_text()

    materialize(manifest, "programme-board", tmp_path / "primary", write=False)
    assert "scenarios" not in yaml.safe_load((tmp_path / "primary/closure.yaml").read_text())

    copied = tmp_path / "changed"
    shutil.copytree(example, copied)
    project = copied / "project.yaml"
    changed = yaml.safe_load(project.read_text())
    changed["scenarios"]["tvac-slip"]["objects"]["tvac"]["schedule"]["amount"] = "20d"
    project.write_text(yaml.safe_dump(changed, sort_keys=False))
    materialize(copied / "manifest.yaml", "tvac-slip", tmp_path / "changed-output", write=True)
    changed_evidence = yaml.safe_load((tmp_path / "changed-output/closure.yaml").read_text())
    assert changed_evidence["scenarios"][0]["contentIdentity"] != evidence["scenarios"][0]["contentIdentity"]
