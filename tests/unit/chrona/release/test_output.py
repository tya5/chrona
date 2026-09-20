from datetime import date
from chrona.release.output import render_output
from chrona.presentation.scene.schedule import Scene


def _scene():
    return Scene("Demo", {"a": {"at": date(2026, 1, 1)}}, {"a": "A"}, (), "Accessible")


def test_output_rejects_required_capability_and_records_permitted_loss():
    raster = {"version": "v2", "target": "raster", "capabilities": {"accessibleText": False}}
    assert render_output(_scene(), "eval:1", raster, {"requires": ["accessibleText"]}).diagnostics == ("E_OUTPUT_CAPABILITY_MISSING",)
    pdf = {"version": "v2", "target": "pdf", "capabilities": {"sourceMetadata": False}}
    result = render_output(_scene(), "eval:1", pdf, {"permitsFidelityLoss": ["sourceMetadata"]})
    assert result.diagnostics == ("E_OUTPUT_TARGET_UNSUPPORTED", "W_OUTPUT_FIDELITY_LOSS")


def test_svg_output_has_deterministic_artifact_and_identity_manifest():
    target = {"version": "v2", "target": "svg", "capabilities": {"sourceMetadata": True, "accessibleText": True}}
    first, second = render_output(_scene(), "eval:1", target), render_output(_scene(), "eval:1", target)
    assert first.artifact == second.artifact and first.manifest["evaluationIdentity"] == "eval:1"
