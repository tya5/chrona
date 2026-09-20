from datetime import date

from chrona.output import render_output
from chrona.release_package import create_release_package, validate_release_package
from chrona.scene import Scene


def _scene():
    return Scene("Demo", {"gate": {"at": date(2026, 10, 1)}}, {"gate": "Gate"}, (), "Accessible")


def _acceptance(disposition="accepted"):
    return {"releaseId": "release-1", "inputClosure": {"evaluationIdentity": "eval-1"}, "output": {"target": "svg", "targetVersion": "chrona/output-capability/v0.2"}, "useCases": [{"id": f"UC-{n:02d}", "disposition": disposition} for n in range(1, 16)]}


def _output():
    return render_output(_scene(), "eval-1", {"version": "chrona/output-capability/v0.2", "target": "svg", "capabilities": {"sourceMetadata": True, "accessibleText": True, "semanticRoles": True}})


def test_release_package_publishes_only_exact_fully_accepted_output():
    output, acceptance = _output(), _acceptance()
    result = create_release_package(acceptance, output)
    assert result.package["status"] == "published" and result.artifact == output.artifact
    assert validate_release_package(result.package, acceptance, output) == ()


def test_release_package_blocks_exclusion_and_rejects_binding_substitution():
    output, acceptance = _output(), _acceptance("excluded")
    blocked = create_release_package(acceptance, output)
    assert blocked.package["status"] == "blocked" and blocked.artifact is None
    published = create_release_package(_acceptance(), output).package
    published["evaluationIdentity"] = "other"
    assert validate_release_package(published, _acceptance(), output) == ("E_RELEASE_BINDING",)
