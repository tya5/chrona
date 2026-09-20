import json
from hashlib import sha256
import sys

import yaml

from chrona.cli import main
from chrona.scheduler import schedule
from chrona.presentation_settings import builtin_bases


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
    for phrase in ("immutable Project snapshot", "diagnostic legacy adapter", "Plan/Actual review"):
        assert phrase in help_text


def test_cli_review_reports_stable_semantic_ids(tmp_path, monkeypatch, capsys):
    before = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {}, "relations": []}
    after = before | {"objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}}
    paths = [tmp_path / "before.yaml", tmp_path / "after.yaml"]
    for path, project in zip(paths, (before, after)): path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "review", str(paths[0]), str(paths[1])])
    main()
    assert json.loads(capsys.readouterr().out)["changes"] == [{"kind": "object", "id": "gate", "change": "added"}]


def test_cli_propose_set_uses_command_without_writing_input(tmp_path, monkeypatch, capsys):
    project = {"version": "timeline/v0.1", "project": {"id": "demo"}, "extensions": [], "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed", "at": "2026-10-01"}}}, "relations": []}
    path = tmp_path / "project.yaml"; path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "propose-set", str(path), "gate", "title", '"Release"'])
    try: main()
    except SystemExit as exit: assert exit.code is False
    assert json.loads(capsys.readouterr().out)["project"]["objects"]["gate"]["fields"]["title"] == "Release"
    assert yaml.safe_load(path.read_text()) == project
