import json
from hashlib import sha256
from pathlib import Path
import sys

import yaml

from chrona.app.cli import main
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


def test_cli_render_review_uses_only_an_immutable_v05_context(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    token = "snapshot-render"
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text())
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text())
    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text())
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text())
    metric_values = {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
        "metric.text-size": 14, "metric.line-height": 1.4,
        "metric.day-width": 12, "metric.row-height": 40, "metric.axis-height": 48,
        "metric.column-width": 120, "metric.header-height": 44,
    }
    theme["body"]["values"].update({name: {"type": "number", "value": value} for name, value in metric_values.items()})
    theme["body"]["metrics"] = {
        "text.body.size": "metric.text-size", "text.body.lineHeight": "metric.line-height",
        "timeline.dayWidth": "metric.day-width",
        "timeline.row.minBlockSize": "metric.row-height", "timeline.axis.blockSize": "metric.axis-height",
        "table.column.minInlineSize": "metric.column-width", "table.header.blockSize": "metric.header-height",
    }
    theme["body"]["roles"]["dependency"] = {"stroke": "grid"}
    old_values, old_roles = theme["body"]["values"], theme["body"]["roles"]
    intent = {"canvas": "surface", "ink": "text", "grid": "neutral", "grid-light": "surfaceRaised", "header": "surfaceRaised", "group": "category", "group-firmware": "category", "group-validation": "category", "group-product": "category", "plan": "accent", "actual": "positive", "delay": "warning"}
    bindings, non_color_roles = {}, {}
    for role, properties in old_roles.items():
        retained = {key: value for key, value in properties.items() if key not in {"fill", "stroke"}}
        if retained:
            non_color_roles[role] = retained
        for property_name in ("fill", "stroke"):
            if property_name in properties:
                bindings[f"{role}.{property_name}"] = intent[properties[property_name]]
    theme = {"version": "chrona/theme/v0.2", "kind": "theme", "id": theme["id"], "body": {"values": {key: value for key, value in old_values.items() if value["type"] != "color"}, "roles": non_color_roles, "metrics": theme["body"]["metrics"], "colorBindings": bindings}}
    scheme = {"version": "chrona/color-scheme/v0.1", "kind": "color-scheme", "id": "test-light", "body": {"colors": {"surface": "#FFFFFF", "surfaceRaised": "#E6E9EE", "text": "#172033", "textMuted": "#4B5563", "accent": "#3986E6", "positive": "#269D79", "negative": "#B91C1C", "warning": "#C8762B", "neutral": "#C9CED8"}, "category": ["#E7F0FA", "#E8F6F0", "#FFF4E4"], "suitability": {"background": "light", "colorVision": ["none-claimed"], "print": "not-claimed"}, "provenance": {"kind": "chrona-authored", "source": "test", "license": "pending"}}}
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
