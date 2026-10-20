from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import shutil
import sys
import time
import subprocess
import json
from types import MappingProxyType

import pytest
import yaml

from chrona.resources import safe_load
from chrona.usecases.materialize import _OverlayBuilder, copy_context_closure
from chrona.usecases.render_review import RenderFailed
from tools import check_draft_viewport_matrix as matrix
from tests.support.deck_contexts import slide_context


ROOT = Path(__file__).resolve().parents[3]
ROADMAP = ROOT / "examples/chrona-roadmap"
ROADMAP_SLIDE = "roadmap"


def _delayed_value(task):
    value, delay = task
    time.sleep(delay)
    return value


def _prepared_roadmap(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    overlay_builder = _OverlayBuilder(tmp_path / "overlay")
    decoded_catalogs = {}
    selected = slide_context(ROADMAP, ROADMAP_SLIDE)
    original_bytes = selected.payload
    context = safe_load(original_bytes)
    original_reference, _revision = copy_context_closure(
        ROADMAP, selected, snapshot,
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
    assert slide_context(ROADMAP, ROADMAP_SLIDE).payload == context_bytes
    assert all(path.read_bytes() == payload and matrix._content_identity(payload) == identity
               for path, payload, identity in staged_references.values())
    assert all(path.read_bytes() == payload and matrix._content_identity(payload) == identity
               for path, payload, identity in staged_assets.values())


def test_viewport_targets_are_manifest_selected_composed_sources(tmp_path):
    root = tmp_path
    example = root / "examples/demo"
    shutil.copytree(ROOT / "tests/fixtures/aster-ssd", example)
    context = safe_load((example / "contexts/01-overview.yaml").read_bytes())
    manifest = {
        "version": "chrona/example-materializer/v0.1", "id": "demo",
        "role": "regression-corpus", "contextDefaults": context["body"],
        "slides": [{"id": "overview", "evidence": "shared", "expectedSvg": "generated/overview.svg",
                    "contextOverrides": {"id": context["id"]}}],
    }
    manifest_path = example / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    targets, identifiers = matrix._viewport_targets(root)

    assert targets == ((manifest_path, "overview"),)
    assert identifiers == {f"demo/overview@{width}x{height}" for width, height in matrix.VIEWPORTS}


@pytest.mark.parametrize("immutable", [False, True])
def test_derived_context_identity_changes_only_context_id_and_viewport(tmp_path, immutable):
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
        MappingProxyType(source) if immutable else source,
        reference, Path("original.yaml"), (800, 450), builder,
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
        context, original_ref, original_ref["address"], (800, 450), builder,
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
        context, original_ref, original_ref["address"], (800, 450), builder,
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


def test_all_25_capacity_cases_remain_explicitly_recorded():
    expectations = matrix._load_expectations()
    assert len(expectations) == 25
    for item in expectations.values():
        diagnostic = item["diagnostics"][0]
        assert diagnostic["code"] == "E_LAYOUT_TEMPORAL_INLINE_CAPACITY"
        assert diagnostic["sourceRef"] == "/layoutManifest/sources/timeline"
        assert all(field in diagnostic["message"] for field in (
            "slot=", "allocated_inline=", "required_inline="))


def test_four_additional_roadmap_cases_remain_separate_from_the_original_21():
    expectations = matrix._load_expectations()
    additions = {
        "chrona-roadmap/marquee@800x450",
        "chrona-roadmap/marquee@600x340",
        "chrona-roadmap/titlecard@600x340",
        "chrona-roadmap/yuya@600x340",
    }
    assert additions <= expectations.keys()
    assert len(expectations.keys() - additions) == 21
    assert len({expectations[key]["diagnostics"][0]["message"] for key in additions}) == 4


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
    message = "E_LAYOUT_PATH_INPUT: open span requires positive inline_size"
    observed = matrix._failure_outcome(ValueError(message))
    assert observed["exitCode"] == 1
    assert observed["diagnostics"][0]["code"] == "E_LAYOUT_PATH_INPUT"
    assert observed["diagnostics"][0]["message"] == message
