from pathlib import Path

import yaml


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


def test_one_readiness_job_freezes_sha_for_all_scheduled_consumers_without_bypassing_failure():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    workflow = yaml.load((root / ".github/workflows/conformance.yml").read_text(encoding="utf-8"),
                         Loader=yaml.BaseLoader)
    jobs = workflow["jobs"]
    readiness = jobs["ready-sha"]
    assert readiness["timeout-minutes"] == "2"
    assert readiness["outputs"]["sha"] == "${{ steps.resolve.outputs.sha }}"
    assert any(step.get("run") == "python tools/scheduled_readiness.py" for step in readiness["steps"])
    assert readiness["steps"][-1]["env"]["SELECT_READY_MAIN"] == "${{ inputs.select_ready_main }}"
    assert workflow["on"]["workflow_dispatch"]["inputs"]["select_ready_main"]["default"] == "false"

    expected_checkout = "${{ needs.ready-sha.outputs.sha }}"
    for name in ("full-matrix", "reproduction-newest-python", "mcp-floor"):
        job = jobs[name]
        assert "ready-sha" in job["needs"], name
        assert "needs.ready-sha.result == 'success'" in job["if"], name
        checkout = next(step for step in job["steps"]
                        if step.get("uses", "").startswith("actions/checkout@"))
        assert checkout["with"]["ref"] == expected_checkout, name

    # The immutable selector is a pass-through for ordinary dispatch, leaving
    # the existing exact-SHA release check intact.
    full = jobs["full-matrix"]
    guard = next(step for step in full["steps"]
                 if step.get("name") == "Verify exact full-CI SHA when supplied")
    assert 'test "$GITHUB_SHA" = "$EXPECTED_SHA"' in guard["run"]


def test_workflow_installs_the_mcp_extra_where_the_mcp_tests_must_run_and_pins_the_tested_floor():
    import re
    import tomllib

    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    workflow = (root / ".github/workflows/conformance.yml").read_text(encoding="utf-8")
    jobs = {name: body for name, body in re.findall(r"^  ([a-z][a-z-]*):\n(.*?)(?=^  [a-z][a-z-]*:\n|\Z)", workflow, re.S | re.M)}
    extra = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]["mcp"]
    floor = re.fullmatch(r"mcp>=([0-9.]+),<[0-9.]+", extra[0])

    assert len(extra) == 1 and floor, extra
    # The Ubuntu PR shards and the three-OS release matrix run tests/mcp against the newest SDK the extra allows.
    for job in ("pr-pytest", "full-matrix"):
        assert "pip install -e '.[dev,render,mcp]' -e packages/chrona-fonts-noto-cjk" in jobs[job], job
    # Every other job installs without it: the extra is optional and must stay optional.
    for job in ("derived-preview", "pr-conformance", "reproduction-newest-python"):
        assert "mcp" not in jobs[job].replace("tests/mcp", ""), job
    # A separate job runs the same tests against the declared floor, so the floor is tested, not only named.
    from packaging.version import Version

    pinned = re.search(r"'mcp==([0-9.]+)'", jobs["mcp-floor"])
    assert pinned and Version(pinned.group(1)) == Version(floor.group(1)) and "tests/mcp" in jobs["mcp-floor"]
    assert "mcp-floor" not in re.search(r"derived-ready:\n    needs: \[([^\]]*)\]", workflow).group(1)


def test_the_wheel_job_runs_the_documented_commands_against_the_built_wheel():
    workflow = (Path(__file__).resolve().parents[3] / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
    assert "tools/wheel_doc_check.py dist/chrona-*.whl" in workflow
