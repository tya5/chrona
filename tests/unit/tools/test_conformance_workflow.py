from pathlib import Path


def test_conformance_workflow_reports_independent_gate_and_pytest_outcomes():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    workflow = (root / ".github/workflows/conformance.yml").read_text(encoding="utf-8")

    assert "fail-fast: false" in workflow
    assert "id: conformance" in workflow and "id: pytest" in workflow and "id: wheel_smoke" in workflow
    assert "if: ${{ always() }}" in workflow
    assert "continue-on-error: true" in workflow
    assert "Finalize independent CI outcomes" in workflow
    assert "tools/check_ci_outcomes.py" in workflow
    assert "steps.conformance.outcome" in workflow and "steps.pytest.outcome" in workflow
