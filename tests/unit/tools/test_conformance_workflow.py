from pathlib import Path


def test_conformance_workflow_routes_prs_and_preserves_full_release_matrix():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    workflow = (root / ".github/workflows/conformance.yml").read_text(encoding="utf-8")

    assert "fail-fast: false" in workflow
    assert "classify-pr:" in workflow
    assert "pr-conformance:" in workflow and "pr-pytest:" in workflow
    assert "full-matrix:" in workflow
    assert "schedule:" in workflow and "workflow_dispatch:" in workflow
    assert "os: [ubuntu-latest, macos-latest, windows-latest]" in workflow
    assert "shard: [1, 2, 3]" in workflow
    assert "--splits 3 --group ${{ matrix.shard }}" in workflow
    assert "id: conformance" in workflow and "id: pytest" in workflow and "id: wheel_smoke" in workflow
    assert "if: ${{ always() }}" in workflow
    assert "continue-on-error: true" in workflow
    assert "Finalize independent CI outcomes" in workflow
    assert "tools/check_ci_outcomes.py" in workflow
    assert "steps.conformance.outcome" in workflow and "steps.pytest.outcome" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow
    assert "github.event.pull_request.number || github.run_id" in workflow
    assert "os_failure_probe" in workflow
