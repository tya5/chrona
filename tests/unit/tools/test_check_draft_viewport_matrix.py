from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
import time
import subprocess

import pytest
import yaml

from chrona.resources import safe_load
from chrona.usecases.materialize import _OverlayBuilder, copy_context_closure
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
