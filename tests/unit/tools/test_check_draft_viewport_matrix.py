from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
import time
import subprocess
import json

import pytest
import yaml

from chrona.resources import safe_load
from chrona.usecases.materialize import _OverlayBuilder, copy_context_closure
from chrona.usecases.render_review import RenderFailed
from tools import check_draft_viewport_matrix as matrix


ROOT = Path(__file__).resolve().parents[3]
ROADMAP = ROOT / "examples/chrona-roadmap"
ROADMAP_CONTEXT = ROADMAP / "contexts/roadmap.yaml"


def _delayed_value(task):
    value, delay = task
    time.sleep(delay)
    return value


def _prepared_roadmap(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    overlay_builder = _OverlayBuilder(tmp_path / "overlay")
    decoded_catalogs = {}
    original_bytes = ROADMAP_CONTEXT.read_bytes()
    context = safe_load(original_bytes)
    original_reference, _revision = copy_context_closure(
        ROADMAP, ROADMAP_CONTEXT, snapshot,
        decoded_catalogs=decoded_catalogs,
        overlay_builder=overlay_builder,
    )
    staged_references = {
        key: (path, path.read_bytes(), identity)
        for key, (path, _expected, identity) in overlay_builder.references.items()
    }
    staged_assets = {
        key: (path, path.read_bytes(), identity)
        for key, (path, _expected, identity) in overlay_builder.assets.items()
    }
    return (snapshot, overlay_builder, decoded_catalogs, context, original_reference,
            original_bytes, staged_references, staged_assets)


def _assert_sources_unchanged(context_bytes, staged_references, staged_assets):
    assert ROADMAP_CONTEXT.read_bytes() == context_bytes
    assert all(path.read_bytes() == payload and matrix._content_identity(payload) == identity
               for path, payload, identity in staged_references.values())
    assert all(path.read_bytes() == payload and matrix._content_identity(payload) == identity
               for path, payload, identity in staged_assets.values())


def test_derived_context_identity_changes_only_context_id_and_viewport(tmp_path):
    source = {
        "version": "chrona/render-context/v0.17",
        "kind": "render-context",
        "id": "synthetic-context",
        "body": {
            "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US"},
            "inputs": {"snapshot": {"id": "snapshot-1", "revision": {"token": "r7"}}},
        },
    }
    reference = {
        "id": "synthetic-context", "kind": "render-context",
        "store": {"provider": "local", "identity": "synthetic"},
        "address": "contexts/original.yaml", "revision": {"token": "r7"},
        "contentIdentity": "sha256:" + sha256(b"original context").hexdigest(),
    }
    original_inputs = deepcopy(source["body"]["inputs"])
    builder = _OverlayBuilder(tmp_path)
    builder.add_reference(reference, b"original context")
    original_overlay = builder.finish()

    derived_ref, payload = matrix._derive_viewport_context(
        source, reference, Path("original.yaml"), (800, 450), builder,
    )
    derived = yaml.safe_load(payload)
    expected = deepcopy(source)
    expected["id"] = "synthetic-context-viewport-800x450"
    expected["body"]["environment"]["viewport"] = {"inlineSize": 800, "blockSize": 450}

    assert derived == expected
    assert derived["body"]["inputs"] == original_inputs
    assert derived_ref["revision"] == reference["revision"]
    assert derived_ref["store"] == reference["store"]
    assert derived_ref["address"] != reference["address"]
    assert derived_ref["id"] != reference["id"]
    assert derived_ref["contentIdentity"] == "sha256:" + sha256(payload).hexdigest()
    assert original_overlay.read(reference) == b"original context"
    assert builder.finish().read(derived_ref) == payload


def test_context_api_matrix_path_retains_snapshot_and_authored_bytes(tmp_path):
    (snapshot, builder, decoded_catalogs, context, original_ref, source_bytes,
     staged_references, staged_assets) = _prepared_roadmap(tmp_path)
    original_inputs = deepcopy(context["body"].get("inputs", {}))
    reference, _payload = matrix._derive_viewport_context(
        context, original_ref, ROADMAP_CONTEXT, (800, 450), builder,
    )
    overlay = builder.finish()

    rendered = matrix._render_api(reference, overlay, decoded_catalogs, snapshot)
    bounds = matrix._validate_artifact(rendered.artifact.content)

    assert all(abs(actual - serialized) < .0011 for actual, serialized in
               zip(rendered.surface.canvas_bounds, bounds, strict=True))
    assert {"snapshot-ref", "snapshot-project"} <= rendered.read_inputs
    assert any(item.source_kind == "snapshot" or item.visual_role == "snapshot"
               for item in rendered.surface.primitives)
    assert safe_load(overlay.read(reference))["body"]["inputs"] == original_inputs
    _assert_sources_unchanged(source_bytes, staged_references, staged_assets)


def test_context_cli_matrix_path_uses_public_render_review(tmp_path):
    (snapshot, builder, _decoded_catalogs, context, original_ref, source_bytes,
     staged_references, staged_assets) = _prepared_roadmap(tmp_path)
    reference, payload = matrix._derive_viewport_context(
        context, original_ref, ROADMAP_CONTEXT, (800, 450), builder,
    )

    artifact, _warnings = matrix._render_cli(
        reference, payload, snapshot, tmp_path, (800, 450),
    )

    assert matrix._validate_artifact(artifact)[2:] != (0, 0)
    _assert_sources_unchanged(source_bytes, staged_references, staged_assets)


@pytest.mark.parametrize("interpreter", ["C:/Python/python.exe", "/venv/bin/python"])
def test_cli_uses_the_same_interpreter_without_assuming_console_script_location(tmp_path, monkeypatch, interpreter):
    monkeypatch.setattr(sys, "executable", interpreter)
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        Path(command[command.index("--output") + 1]).write_bytes(b"synthetic artifact")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(matrix.subprocess, "run", run)
    reference = {"revision": {"token": "r1"}, "address": "contexts/synthetic.yaml",
                 "store": {"identity": "synthetic-store"}}
    artifact, warnings = matrix._render_cli(reference, b"synthetic context", tmp_path / "snapshot", tmp_path, (800, 450))
    assert commands[0][:4] == [interpreter, "-m", "chrona", "render-review"]
    assert "--reject-unused-closure-inputs" in commands[0]
    assert artifact == b"synthetic artifact" and warnings == 0


def test_parallel_group_results_keep_submission_order():
    tasks = (("first", .15), ("second", 0), ("third", .03))

    assert matrix._ordered_map(_delayed_value, tasks, jobs=3) == ("first", "second", "third")


def test_jobs_must_be_positive(tmp_path, monkeypatch):
    monkeypatch.setattr(matrix, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["check_draft_viewport_matrix.py", "--jobs", "0"])

    with pytest.raises(SystemExit) as raised:
        matrix.main()

    assert raised.value.code == 2


def test_all_21_capacity_cases_remain_explicitly_recorded():
    expectations = matrix._load_expectations()
    assert len(expectations) == 21
    assert sum(item["diagnostics"][0]["code"] == "E_LAYOUT_MARK_OVERFLOW"
               for item in expectations.values()) == 13
    assert sum(item["diagnostics"][0]["code"] == "E_LAYOUT_LANE_SEED_INVALID"
               for item in expectations.values()) == 6
    assert sum(item["diagnostics"][0]["code"] == "E_LAYOUT_PATH_INPUT"
               for item in expectations.values()) == 2


def test_expected_refusal_matches_complete_public_diagnostic_not_only_code():
    expected = matrix._load_expectations()["chrona-roadmap/roadmap@600x340"]
    diagnostic = expected["diagnostics"][0]
    error = RenderFailed(diagnostic["code"], diagnostic["message"],
                         diagnostic["component"], diagnostic["sourceRef"])
    observed = matrix._failure_outcome(error)
    expectations = {"synthetic/context@600x340": expected}
    assert matrix._outcome_mismatch("synthetic/context@600x340", observed, expectations) is None
    for key, value in (("code", "E_OTHER"), ("message", "changed failure"),
                       ("sourceRef", "/another-source"), ("component", "closure")):
        changed = deepcopy(observed)
        changed["diagnostics"][0][key] = value
        assert matrix._outcome_mismatch("synthetic/context@600x340", changed, expectations)
    changed = deepcopy(observed)
    changed["exitCode"] = 2
    assert matrix._outcome_mismatch("synthetic/context@600x340", changed, expectations)


def test_unexpected_success_and_unlisted_failure_are_reported():
    expected = matrix._load_expectations()["chrona-roadmap/roadmap@600x340"]
    expectations = {"expected": expected}
    assert matrix._outcome_mismatch("expected", None, expectations)
    assert matrix._outcome_mismatch("unlisted", expected, expectations)
    assert matrix._outcome_mismatch("unlisted", None, expectations) is None


def test_retired_expected_case_fails_instead_of_silently_disappearing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(matrix, "ROOT", tmp_path)
    monkeypatch.setattr(matrix, "_load_expectations", lambda: {"missing@600x340": {}})
    monkeypatch.setattr(sys, "argv", ["check_draft_viewport_matrix.py"])
    assert matrix.main() == 1
    assert "missing@600x340: expected refusal case is missing" in capsys.readouterr().out


@pytest.mark.parametrize("identifier", ["chrona-roadmap/roadmap@600x340",
    "halcyon-1/02-programme-board@600x340", "controller-z/annotation-rounded@600x340"])
def test_cli_failure_retains_exact_report_and_exit_code(tmp_path, monkeypatch, identifier):
    expected = matrix._load_expectations()[identifier]
    payload = {key: value for key, value in expected.items() if key != "exitCode"}
    monkeypatch.setattr(matrix.subprocess, "run", lambda *args, **kwargs:
        subprocess.CompletedProcess(args[0], expected["exitCode"],
                                    stdout=json.dumps(payload, indent=2), stderr=""))
    reference = {"revision": {"token": "r1"}, "address": "contexts/synthetic.yaml",
                 "store": {"identity": "synthetic-store"}}
    with pytest.raises(matrix.CliRenderFailure) as raised:
        matrix._render_cli(reference, b"synthetic context", tmp_path / "snapshot", tmp_path, (600, 340))
    assert matrix._failure_outcome(raised.value) == expected


def test_raw_path_value_error_uses_existing_failure_reporter():
    expected = matrix._load_expectations()["controller-z/annotation-rounded@600x340"]
    error = ValueError(expected["diagnostics"][0]["message"])
    assert matrix._failure_outcome(error) == expected
