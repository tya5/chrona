import json
from hashlib import sha256
from pathlib import Path
import sys

import yaml

from chrona.app.cli import main
from chrona.scheduling.scheduler import schedule
from chrona.presentation.model.settings import builtin_bases


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


def test_cli_render_can_select_the_common_v2_scene_path(tmp_path, monkeypatch):
    project = {"version": "timeline/v0.1", "project": {"id": "demo", "title": "Demo"},
               "extensions": [], "objects": {"gate": {"type": "milestone", "title": "Gate",
               "schedule": {"mode": "fixed", "at": "2026-10-01"}}}, "relations": []}
    project_path, settings_path, output = tmp_path / "project.yaml", tmp_path / "settings.json", tmp_path / "v2.svg"
    project_path.write_text(yaml.safe_dump(project))
    settings = builtin_bases()["executive-v0.2"]
    settings_path.write_text(json.dumps(settings))
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project_path), "--output", str(output),
                                      "--presentation-settings", str(settings_path)])
    main()
    svg = output.read_text()
    assert 'data-surface-id="minimal"' in svg
    assert "E_PRESENTATION_LEGACY_ADAPTER" not in svg


def test_cli_help_describes_all_commands(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "--help"])
    try:
        main()
    except SystemExit as exit:
        assert exit.code == 0
    help_text = capsys.readouterr().out
    for phrase in ("immutable Project snapshot", "diagnostic legacy adapter", "immutable Render Context v0.3"):
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


def test_cli_propose_set_uses_command_without_writing_input(tmp_path, monkeypatch, capsys):
    project = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}, "relations": []}
    path = tmp_path / "project.yaml"; path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "propose-set", str(path), "gate", "title", "--value", "Release"])
    main()
    assert json.loads(capsys.readouterr().out)["project"]["objects"]["gate"]["fields"]["title"] == "Release"
    assert yaml.safe_load(path.read_text()) == project


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


def test_cli_propose_set_distinguishes_literal_and_json_values(tmp_path, monkeypatch, capsys):
    project = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}, "relations": []}
    path = tmp_path / "project.yaml"; path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "propose-set", str(path), "gate", "rank", "--value-json", "3"])
    main()
    assert json.loads(capsys.readouterr().out)["project"]["objects"]["gate"]["fields"]["rank"] == 3


def test_cli_render_review_uses_only_an_immutable_v03_context(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    token = "snapshot-render"
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text())
    view = yaml.safe_load((root / "examples/controller-z/shared/view.yaml").read_text())
    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text())
    preset = yaml.safe_load((root / "examples/controller-z/variants/review-detail/settings.yaml").read_text())
    detail = yaml.safe_load((root / "examples/controller-z/variants/review-detail/detail.yaml").read_text())
    refs = {
        "project": _snapshot_resource(tmp_path, token, "project.yaml", project, "project", project["project"]["id"]),
        "view": _snapshot_resource(tmp_path, token, "view.yaml", view, "view", view["id"]),
        "actual": _snapshot_resource(tmp_path, token, "actual.yaml", actual, "actual-set", actual["id"]),
        "preset": _snapshot_resource(tmp_path, token, "preset.yaml", preset, "presentation-preset", preset["id"]),
        "detail": _snapshot_resource(tmp_path, token, "detail.yaml", detail, "review-detail-profile", detail["id"]),
    }
    context = {
        "version": "chrona/presentation/v0.3", "kind": "render-context", "id": "controller-z-current",
        "body": {
            "project": refs["project"], "view": refs["view"], "presentationPreset": refs["preset"],
            "inputs": {"actual": refs["actual"], "detailProfile": refs["detail"]},
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
    assert 'data-surface-id="table-timeline"' in output.read_text(encoding="utf-8")
