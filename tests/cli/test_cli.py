import json
from hashlib import sha256
from pathlib import Path
import sys

import yaml
import pytest

import chrona.app.cli as cli
from chrona.app.cli import CliFailure, main
from chrona.presentation.model.closure import ClosureResource
from chrona.scheduling.scheduler import schedule


def _snapshot_resource(root, token, address, value, kind, identifier, identity="cli-test"):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = root / token / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "id": identifier, "kind": kind,
        "store": {"provider": "local", "identity": identity},
        "address": address, "revision": {"token": token},
        "contentIdentity": "sha256:" + sha256(payload).hexdigest(),
    }


def test_cli_schedule_matches_library_result(tmp_path, monkeypatch, capsys):
    project = {
        "version": "timeline/v0.1",
        "project": {"id": "demo", "title": "Demo"},
        "extensions": [],
        "objects": {"gate": {"type": "milestone", "title": "Gate", "schedule": {"mode": "fixed", "at": "2026-10-01"}}},
        "relations": [],
    }
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "schedule", str(path)])
    try:
        main()
    except SystemExit as exit:
        assert exit.code is False
    output = json.loads(capsys.readouterr().out)
    assert output["placements"] == {"gate": {"at": "2026-10-01"}}
    assert output["placements"] == json.loads(json.dumps(schedule(project).placements, default=str))


def test_cli_render_consumes_scene_adapter(tmp_path, monkeypatch):
    project = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}, "relations": []}
    path, output = tmp_path / "project.yaml", tmp_path / "timeline.svg"
    path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(path), "--output", str(output)])
    main()
    assert "<svg " in output.read_text(encoding="utf-8")


def test_cli_schedule_reads_an_immutable_snapshot_without_path_fallback(tmp_path, monkeypatch, capsys):
    project = {
        "version": "timeline/v0.1", "project": {"id": "snapshot"}, "extensions": [],
        "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}},
        "relations": [],
    }
    payload = yaml.safe_dump(project).encode()
    token = "snapshot-1"
    (tmp_path / token).mkdir()
    (tmp_path / token / "project.yaml").write_bytes(payload)
    reference = {
        "kind": "project",
        "store": {"provider": "local", "identity": "cli-test"},
        "revision": {"token": token},
        "address": "project.yaml",
        "contentIdentity": "sha256:" + sha256(payload).hexdigest(),
    }
    reference_path = tmp_path / "reference.yaml"
    reference_path.write_text(yaml.safe_dump(reference))
    monkeypatch.setattr(sys, "argv", ["chrona", "schedule", "--snapshot-reference", str(reference_path),
                                      "--snapshot-root", str(tmp_path), "--store-identity", "cli-test"])
    try:
        main()
    except SystemExit as exit:
        assert exit.code is False
    assert json.loads(capsys.readouterr().out)["placements"] == {"gate": {"at": "2026-10-01"}}


def test_cli_help_describes_all_commands(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "--help"])
    try:
        main()
    except SystemExit as exit:
        assert exit.code == 0
    help_text = capsys.readouterr().out
    for phrase in ("immutable Project snapshot", "minimal schedule scene", "immutable Render Context v0.5"):
        assert phrase in help_text


def test_cli_review_reports_stable_semantic_ids(tmp_path, monkeypatch, capsys):
    before = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {}, "relations": []}
    after = before | {"objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}}
    token = "snapshot-review"
    references = [
        _snapshot_resource(tmp_path, token, f"{name}.yaml", project, "project", "demo")
        for name, project in (("before", before), ("after", after))
    ]
    paths = [tmp_path / "before-ref.yaml", tmp_path / "after-ref.yaml"]
    for path, reference in zip(paths, references): path.write_text(yaml.safe_dump(reference), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "review", str(paths[0]), str(paths[1]),
                                      "--snapshot-root", str(tmp_path), "--store-identity", "cli-test"])
    main()
    assert json.loads(capsys.readouterr().out)["changes"] == [{"kind": "object", "id": "gate", "change": "added"}]


def test_cli_baseline_compare_uses_store_config_and_writes_once(tmp_path, monkeypatch):
    before = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {}, "relations": []}
    after = before | {"objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}}
    token = "snapshot"
    before_ref = _snapshot_resource(tmp_path, token, "before.yaml", before, "project", "demo")
    candidate_ref = _snapshot_resource(tmp_path, token, "after.yaml", after, "project", "demo")
    baseline = {"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "q2", "body": {"project": before_ref}}
    baseline_payload = yaml.safe_dump(baseline, sort_keys=True).encode()
    baseline_path = tmp_path / "snapshots" / "q2.yaml"; baseline_path.parent.mkdir(); baseline_path.write_bytes(baseline_payload)
    digest = sha256(baseline_payload).hexdigest()
    baseline_ref = {"id": "q2", "kind": "snapshot-ref", "store": {"provider": "local", "identity": "cli-test"}, "address": "snapshots/q2.yaml", "revision": {"token": "baseline:" + digest}, "contentIdentity": "sha256:" + digest}
    for path, value in ((tmp_path / "baseline-ref.yaml", baseline_ref), (tmp_path / "candidate-ref.yaml", candidate_ref), (tmp_path / "stores.yaml", {"version": "chrona/store-config/v0.1", "stores": [{"provider": "local", "identity": "cli-test", "root": str(tmp_path)}]})):
        path.write_text(yaml.safe_dump(value), encoding="utf-8")
    result = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", ["chrona", "baseline-compare", "--baseline-reference", str(tmp_path / "baseline-ref.yaml"), "--candidate-reference", str(tmp_path / "candidate-ref.yaml"), "--store-config", str(tmp_path / "stores.yaml"), "--result", str(result)])
    main()
    assert json.loads(result.read_text())["comparison"]["changes"][0]["id"] == "gate"
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2


def test_cli_command_check_writes_non_mutating_result(tmp_path, monkeypatch):
    project = {"version": "timeline/v0.1", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    target = _snapshot_resource(tmp_path, "p-r1", "project.yaml", project, "project", "p")
    command = {"version": "chrona/command/v0.2", "commandId": "check-1", "type": "captureSnapshot", "target": target, "baseRevision": target["revision"]["token"], "expectedContentIdentity": target["contentIdentity"], "payload": {"snapshotId": "q2", "registry": {"provider": "local", "identity": "cli-test"}}}
    command_path, config_path, result = tmp_path / "command.yaml", tmp_path / "stores.yaml", tmp_path / "result.json"
    command_path.write_text(yaml.safe_dump(command)); config_path.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [{"provider": "local", "identity": "cli-test", "root": str(tmp_path)}]}))
    monkeypatch.setattr(sys, "argv", ["chrona", "command-check", "--command", str(command_path), "--store-config", str(config_path), "--result", str(result)])
    main()
    assert json.loads(result.read_text())["status"] == "accepted"


def test_cli_operational_request_read_failure_is_exit_three(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "command-check", "--command", str(tmp_path / "missing.yaml"), "--store-config", str(tmp_path / "stores.yaml"), "--result", str(tmp_path / "result.json")])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 3
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_AUTOMATION_RESULT_IO"


def test_cli_failures_are_one_json_envelope_without_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "schedule", str(tmp_path / "missing.yaml")])
    try:
        main()
    except SystemExit as error:
        assert error.code == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "failed"
    assert payload["diagnostics"][0]["code"] == "E_INPUT_IO"
    assert set(payload["diagnostics"][0]) == {"code", "severity", "component", "sourceRef", "revisionRefs", "message"}
    assert "Traceback" not in captured.err


def test_cli_syntax_failure_is_json_and_returns_two(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "render-review"])
    try:
        main()
    except SystemExit as error:
        assert error.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"


def test_cli_gallery_requires_two_contexts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render-review-gallery", "--context-reference", "one.yaml",
        "--snapshot-root", str(tmp_path), "--store-identity", "test",
        "--output-directory", str(tmp_path / "gallery"),
    ])
    try:
        main()
    except SystemExit as error:
        assert error.code == 1
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_SCHEME_GALLERY_INPUT"


def test_cli_gallery_rejects_duplicate_scheme_before_rendering(tmp_path, monkeypatch):
    def closure(_reference, _reader):
        scheme = ClosureResource("color-scheme", "same", "r", "sha256:" + "a" * 64, {})
        return {"id": "context"}, (scheme,)
    monkeypatch.setattr(cli, "resolve_render_context", closure)
    monkeypatch.setattr(cli, "load_yaml", lambda path: {"path": str(path)})
    monkeypatch.setattr(cli, "_run_render_review", lambda args: pytest.fail("render must not run"))
    args = cli.argparse.Namespace(context_reference=["one.yaml", "two.yaml"], snapshot_root=str(tmp_path), store_identity="test", output_directory=str(tmp_path / "gallery"))
    with pytest.raises(CliFailure, match="E_SCHEME_GALLERY_DUPLICATE"):
        cli._run_render_review_gallery(args)


def test_cli_does_not_expose_the_legacy_raw_path_propose_set_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "propose-set"])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"


def test_cli_render_review_uses_only_an_immutable_v05_context(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    token = "snapshot-render"
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text())
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text())
    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text())
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text())
    scheme = yaml.safe_load((root / "examples/controller-z/schemes/executive-light.yaml").read_text())
    layout = yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text())
    refs = {
        "project": _snapshot_resource(tmp_path, token, "project.yaml", project, "project", project["project"]["id"]),
        "view": _snapshot_resource(tmp_path, token, "view.yaml", view, "view", view["id"]),
        "actual": _snapshot_resource(tmp_path, token, "actual.yaml", actual, "actual-set", actual["id"]),
        "theme": _snapshot_resource(tmp_path, token, "theme.yaml", theme, "theme", theme["id"]),
        "colorScheme": _snapshot_resource(tmp_path, token, "scheme.yaml", scheme, "color-scheme", scheme["id"]),
        "layout": _snapshot_resource(tmp_path, token, "layout.yaml", layout, "layout-profile", layout["id"]),
    }
    font_source = root / "src/chrona/resources/font_metrics/nimbus-sans-regular-v1.json"
    font_payload = font_source.read_bytes()
    font_path = tmp_path / token / "font_metrics/nimbus-sans-regular-v1.json"
    font_path.parent.mkdir(parents=True, exist_ok=True); font_path.write_bytes(font_payload)
    context = {
        "version": "chrona/presentation/v0.5", "kind": "render-context", "id": "controller-z-current",
        "body": {
            "project": refs["project"], "view": refs["view"], "theme": refs["theme"], "colorScheme": refs["colorScheme"], "layout": refs["layout"],
            "inputs": {"actual": refs["actual"]},
            "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US", "fontMetrics": {"algorithm": "declared-metrics-v1", "assets": [{"family": "Nimbus Sans", "weight": 400, "revision": "font-v1", "contentIdentity": "sha256:" + sha256(font_payload).hexdigest(), "path": "font_metrics/nimbus-sans-regular-v1.json"}], "missingFont": "diagnose"}, "scenePrecision": 3},
            "target": {"kind": "svg", "capabilities": sorted([
                "sourceMetadata", "accessibleText", "semanticRoles", "marker",
                "tableSemantics", "hierarchicalAxis",
            ])},
        },
    }
    context_ref = _snapshot_resource(tmp_path, token, "context.yaml", context, "render-context", context["id"])
    reference_path, output = tmp_path / "context-ref.yaml", tmp_path / "review.svg"
    reference_path.write_text(yaml.safe_dump(context_ref), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render-review", "--context-reference", str(reference_path),
        "--snapshot-root", str(tmp_path), "--store-identity", "cli-test", "--output", str(output),
    ])
    main()
    rendered = output.read_text(encoding="utf-8")
    assert 'data-source-ref="firmware"' in rendered
    assert 'data-presentation-adapter="legacy-v0.1"' not in rendered
