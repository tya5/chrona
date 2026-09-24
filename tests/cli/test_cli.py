import json
from hashlib import sha256
from pathlib import Path
import sys
import subprocess
from types import SimpleNamespace

import yaml
import pytest

import chrona.app.cli as cli
from chrona.app.cli import CliFailure, main
from chrona.scheduling.scheduler import schedule
from chrona.storage.snapshot_paths import snapshot_directory


def _snapshot_resource(root, token, address, value, kind, identifier, identity="cli-test", payload=None):
    payload = payload if payload is not None else yaml.safe_dump(value, sort_keys=True).encode()
    path = snapshot_directory(root, token) / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "id": identifier, "kind": kind,
        "store": {"provider": "local", "identity": identity},
        "address": address, "revision": {"token": token},
        "contentIdentity": "sha256:" + sha256(payload).hexdigest(),
    }


def test_python_module_entry_point_exposes_the_cli():
    completed = subprocess.run([sys.executable, "-m", "chrona", "--help"], text=True, capture_output=True, check=False)
    assert completed.returncode == 0
    assert "chrona" in completed.stdout


def test_cli_schedule_matches_library_result(tmp_path, monkeypatch, capsys):
    project = {
        "version": "timeline/v0.6",
        "project": {"id": "demo", "title": "Demo"},
        "extensions": [],
        "objects": {"gate": {"type": "milestone", "title": "Gate", "schedule": {"mode": "fixed-point", "at": "2026-10-01"}}},
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
    assert output["analysis"] == {"criticalObjectIds": ["gate"], "totalFloat": {"gate": 0}}


def test_cli_render_requires_draft_review_inputs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chrona", "render", "project.yaml", "--output", "timeline.svg"])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"


@pytest.mark.parametrize(
    ("format_name", "extra", "expected"),
    [
        ("typst", [], "E_RENDER_TYPESETTER_DESCRIPTOR"),
        ("typst", ["--typesetter-engine", "typst"], "E_RENDER_TYPESETTER_DESCRIPTOR"),
        ("svg", ["--typesetter-engine", "typst", "--typesetter-version", "0.13.1", "--typesetter-adapter-grammar", "chrona-typst/v0.1"], "E_RENDER_TYPESETTER_DESCRIPTOR"),
    ],
)
def test_cli_draft_typesetter_descriptor_contract(monkeypatch, capsys, format_name, extra, expected):
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", "project.yaml", "--view", "view.yaml", "--theme", "theme.yaml",
        "--scheme", "scheme.yaml", "--layout", "layout.yaml", "--format", format_name,
        "--output", "output", *extra,
    ])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == expected


def _guided_workspace(tmp_path: Path) -> Path:
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    preset_root = tmp_path / "preset"
    preset_root.mkdir()
    resources = {
        "view.yaml": yaml.safe_load((root / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8")),
        "theme.yaml": yaml.safe_load((root / "examples/aster-ssd/themes/executive-light.yaml").read_text(encoding="utf-8")),
        "scheme.yaml": yaml.safe_load((root / "examples/aster-ssd/schemes/executive-light.yaml").read_text(encoding="utf-8")),
        "layout.yaml": yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8")),
    }
    resources["view.yaml"]["body"]["selection"] = {"include": {"types": ["span"]}}
    resources["view.yaml"]["body"]["comparison"]["actual"] = "optional"
    for name, value in resources.items():
        (preset_root / name).write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    preset = {
        "version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "starter",
        "body": {"package": {"version": "1"}, "resources": {
            "view": {"id": resources["view.yaml"]["id"], "kind": "view", "path": "view.yaml"},
            "theme": {"id": resources["theme.yaml"]["id"], "kind": "theme", "path": "theme.yaml"},
            "colorScheme": {"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"},
            "layout": {"id": resources["layout.yaml"]["id"], "kind": "layout-profile", "path": "layout.yaml"},
        }, "compatibleColorSchemes": [{"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"}]},
    }
    (preset_root / "starter.yaml").write_text(yaml.safe_dump(preset, sort_keys=False), encoding="utf-8")
    workspace = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
        "body": {"project": {"id": "project", "tasks": [{"id": "task", "title": "Task", "planned": {"start": "2026-04-01", "finish": "2026-04-10"}}]},
        "presentation": {"mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset/starter.yaml"}}}},
    }
    path = tmp_path / "workspace.yaml"
    path.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")
    return path


def test_cli_guided_draft_typesetter_descriptor_contract(tmp_path, monkeypatch, capsys):
    workspace = _guided_workspace(tmp_path)
    monkeypatch.setattr(sys, "argv", ["chrona", "render-workspace", str(workspace), "--format", "tikz", "--output", str(tmp_path / "review.tex")])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_RENDER_TYPESETTER_DESCRIPTOR"

    output = tmp_path / "review.tex"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render-workspace", str(workspace), "--format", "tikz",
        "--typesetter-engine", "tectonic", "--typesetter-version", "0.15.0",
        "--typesetter-adapter-grammar", "chrona-tikz/v0.1", "--output", str(output),
    ])
    main()
    assert output.read_bytes().startswith(b"% chrona-tikz/v0.1")


def test_cli_renders_the_plan_only_example_without_an_actual_set(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    output = tmp_path / "plan-only.svg"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/plan-only.yaml"),
        "--theme", str(root / "examples/controller-z/themes/executive-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "examples/controller-z/layouts/executive-review.yaml"),
        "--output", str(output),
    ])

    main()

    assert 'data-source-ref="architecture"' in output.read_text(encoding="utf-8")


def test_cli_render_accepts_a_declared_local_font_closure(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    source = root / "src/chrona/resources"
    font, metrics = source / "fonts/noto-sans-regular-v1.ttf", source / "font_metrics/noto-sans-regular-v1.json"
    local_font, local_metrics = tmp_path / "assets/font.ttf", tmp_path / "assets/metrics.json"
    local_font.parent.mkdir(); local_font.write_bytes(font.read_bytes()); local_metrics.write_bytes(metrics.read_bytes())
    descriptor = {
        "algorithm": "declared-metrics-v2", "missingFont": "diagnose",
        "assets": [{"family": "Noto Sans", "weight": 400,
                    "metrics": {"locator": {"provider": "context", "address": "assets/metrics.json"}, "contentIdentity": "sha256:" + sha256(local_metrics.read_bytes()).hexdigest()},
                    "font": {"locator": {"provider": "context", "address": "assets/font.ttf"}, "contentIdentity": "sha256:" + sha256(local_font.read_bytes()).hexdigest()}}],
    }
    descriptor_path, output = tmp_path / "fonts.yaml", tmp_path / "review.svg"
    descriptor_path.write_text(yaml.safe_dump(descriptor, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/executive.yaml"),
        "--theme", str(root / "examples/controller-z/themes/executive-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "conformance/layout-profile-intent-v0.2.yaml"),
        "--actual", str(root / "examples/controller-z/actual.yaml"),
        "--font-metrics", str(descriptor_path), "--output", str(output),
    ])
    main()
    assert output.read_bytes().startswith(b"<svg")


def test_cli_renders_a_bundled_catalog_icon_with_the_explicit_v07_profile(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    view = yaml.safe_load((root / "examples/controller-z/views/icons.yaml").read_text(encoding="utf-8"))
    for visual in view["body"]["visuals"]:
        if "ref" in visual:
            visual["ref"] = "material:flag-outline-rounded"
        else:
            visual["encoding"]["domain"] = {"fw-team": "material:flag-outline-rounded"}
    view_path = tmp_path / "material-icons.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    output = tmp_path / "material-icons.svg"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(view_path), "--theme", str(root / "examples/controller-z/themes/elevated-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "conformance/layout-profile-intent-v0.2.yaml"),
        "--actual", str(root / "examples/controller-z/actual.yaml"),
        "--icon-catalog", str(root / "src/chrona/resources/icons/material-symbols-outline-rounded-v2026-09-22.yaml"),
        "--visual-profile", "chrona-output/visual/v0.7-svg", "--output", str(output),
    ])

    main()

    assert '<path ' in output.read_text(encoding="utf-8")


def test_cli_icon_import_diagnostic_identifies_the_rejected_icon_source(tmp_path, monkeypatch, capsys):
    source, notice, output = tmp_path / "icons.json", tmp_path / "NOTICE", tmp_path / "icons.yaml"
    source.write_text(json.dumps({"prefix": "demo", "icons": {"bad": {"body": "<defs/>"}}}), encoding="utf-8")
    notice.write_text("MIT\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "chrona", "icon-catalog", "import", str(source), "--license-spdx", "MIT",
        "--notice-file", str(notice), "--output", str(output),
    ])

    with pytest.raises(SystemExit) as exited:
        main()

    assert exited.value.code == 1
    diagnostic = json.loads(capsys.readouterr().out)["diagnostics"][0]
    assert diagnostic == {
        "code": "E_ICON_IMPORT_ELEMENT", "severity": "error", "component": "icon-import",
        "sourceRef": "/defs", "revisionRefs": [],
        "message": "E_ICON_IMPORT_ELEMENT icon=demo:bad source=/defs",
    }


def test_cli_draft_schema_diagnostic_keeps_the_author_facing_explanation(tmp_path, monkeypatch, capsys):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    view = yaml.safe_load((root / "examples/controller-z/views/plan-only.yaml").read_text(encoding="utf-8"))
    view["body"]["visibility"]["relations"] = "invalid"
    view_path = tmp_path / "invalid-view.yaml"
    view_path.write_text(yaml.safe_dump(view, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(view_path), "--theme", str(root / "examples/controller-z/themes/executive-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "examples/controller-z/layouts/executive-review.yaml"),
        "--output", str(tmp_path / "ignored.svg"),
    ])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 1
    diagnostic = json.loads(capsys.readouterr().out)["diagnostics"][0]
    assert diagnostic["code"] == "E_VIEW_SCHEMA"
    assert diagnostic["sourceRef"] == "/body/visibility/relations"
    assert diagnostic["message"] != "E_VIEW_SCHEMA"
    assert diagnostic["message"].startswith("expected one permitted form")


def test_cli_baseline_rejection_keeps_visual_capability_pointer_and_message(tmp_path, monkeypatch, capsys):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/executive.yaml"),
        "--theme", str(root / "examples/controller-z/themes/elevated-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "conformance/layout-profile-intent-v0.2.yaml"),
        "--actual", str(root / "examples/controller-z/actual.yaml"),
        "--visual-profile", "chrona-output/visual/v0.5-baseline", "--output", str(tmp_path / "ignored.svg"),
    ])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 1
    diagnostic = json.loads(capsys.readouterr().out)["diagnostics"][0]
    assert diagnostic == {
        "code": "E_VISUAL_CAPABILITY_UNSUPPORTED", "severity": "error", "component": "presentation",
        "sourceRef": "/body/roles/group-band/gradientAngle", "revisionRefs": [],
        "message": "required visual treatment is not supported by the selected visual profile",
    }


def test_cli_rejects_pdf_rich_profile_before_writing_an_artifact(tmp_path, monkeypatch, capsys):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    output = tmp_path / "forbidden.pdf"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/executive.yaml"),
        "--theme", str(root / "examples/controller-z/themes/elevated-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "conformance/layout-profile-intent-v0.2.yaml"),
        "--actual", str(root / "examples/controller-z/actual.yaml"),
        "--format", "pdf", "--visual-profile", "chrona-output/visual/v0.6-svg", "--output", str(output),
    ])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 1 and not output.exists()
    diagnostic = json.loads(capsys.readouterr().out)["diagnostics"][0]
    assert diagnostic["code"] == "E_VISUAL_CAPABILITY_PROFILE"
    assert diagnostic["sourceRef"] == "/body/target/visualProfile"


def test_cli_renders_typst_draft_with_an_explicit_descriptor(tmp_path, monkeypatch):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    output = tmp_path / "review.typ"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/plan-only.yaml"),
        "--theme", str(root / "examples/controller-z/themes/executive-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "examples/controller-z/layouts/executive-review.yaml"),
        "--format", "typst", "--typesetter-engine", "typst", "--typesetter-version", "0.13.1",
        "--typesetter-adapter-grammar", "chrona-typst/v0.1", "--output", str(output),
    ])

    main()

    assert output.read_bytes().startswith(b"// chrona-typst/v0.1")


def test_cli_schedule_analysis_uses_project_order_and_halcyon_facts(tmp_path, monkeypatch, capsys):
    project = {
        "version": "timeline/v0.6", "project": {"id": "ordered"}, "extensions": [],
        "objects": {
            "second": {"type": "milestone", "title": "Second", "schedule": {"mode": "fixed-point", "at": "2026-10-02"}},
            "first": {"type": "milestone", "title": "First", "schedule": {"mode": "fixed-point", "at": "2026-10-01"}},
        }, "relations": [],
    }
    path = tmp_path / "ordered.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "schedule", str(path)])
    main()
    assert json.loads(capsys.readouterr().out)["analysis"]["criticalObjectIds"] == ["second", "first"]

    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    halcyon = yaml.safe_load((root / "examples/halcyon-1/project.yaml").read_text(encoding="utf-8"))
    monkeypatch.setattr(sys, "argv", ["chrona", "schedule", str(root / "examples/halcyon-1/project.yaml")])
    main()
    payload = json.loads(capsys.readouterr().out)
    expected = schedule(halcyon).analysis
    assert payload["analysis"] == {
        "criticalObjectIds": [object_id for object_id in halcyon["objects"] if object_id in expected.critical],
        "totalFloat": expected.total_float,
    }


def test_cli_schedule_rejection_has_no_analysis_payload(tmp_path, monkeypatch, capsys):
    project = {
        "version": "timeline/v0.6", "project": {"id": "invalid"}, "extensions": [],
        "objects": {
            "a": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
            "b": {"type": "task", "schedule": {"mode": "scheduled", "amount": "1d"}},
        },
        "relations": [
            {"type": "dependency", "from": {"object": "a", "endpoint": "start"}, "to": {"object": "b", "endpoint": "start"}, "lag": "0d"},
            {"type": "dependency", "from": {"object": "b", "endpoint": "start"}, "to": {"object": "a", "endpoint": "start"}, "lag": "0d"},
        ],
    }
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(project), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "schedule", str(path)])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "rejected"
    assert "analysis" not in payload


def test_cli_schedule_reads_an_immutable_snapshot_without_path_fallback(tmp_path, monkeypatch, capsys):
    project = {
        "version": "timeline/v0.6", "project": {"id": "snapshot"}, "extensions": [],
        "objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-10-01"}}},
        "relations": [],
    }
    payload = yaml.safe_dump(project).encode()
    token = "snapshot-1"
    snapshot_directory(tmp_path, token).mkdir()
    (snapshot_directory(tmp_path, token) / "project.yaml").write_bytes(payload)
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
    for phrase in ("immutable Project snapshot", "draft review surface", "immutable Render Context v0.8"):
        assert phrase in help_text


def test_cli_review_reports_stable_semantic_ids(tmp_path, monkeypatch, capsys):
    before = {"version": "timeline/v0.6", "project": {"id": "demo"}, "extensions": [], "objects": {}, "relations": []}
    after = before | {"objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-10-01"}}}}
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
    before = {"version": "timeline/v0.6", "project": {"id": "demo"}, "extensions": [], "objects": {}, "relations": []}
    after = before | {"objects": {"gate": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-10-01"}}}}
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
    assert json.loads(result.read_text(encoding="utf-8"))["comparison"]["changes"][0]["id"] == "gate"
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2


def test_cli_result_write_does_not_require_hard_link_support(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.os, "link", lambda *_args: (_ for _ in ()).throw(OSError("unsupported")))
    destination = tmp_path / "result.json"
    cli._write_result(destination, {"status": "accepted"})
    assert json.loads(destination.read_text(encoding="utf-8")) == {"status": "accepted"}


def test_cli_command_check_writes_non_mutating_result(tmp_path, monkeypatch):
    project = {"version": "timeline/v0.6", "project": {"id": "p"}, "extensions": [], "objects": {}, "relations": []}
    target = _snapshot_resource(tmp_path, "p-r1", "project.yaml", project, "project", "p")
    command = {"version": "chrona/command/v0.2", "commandId": "check-1", "type": "captureSnapshot", "target": target, "baseRevision": target["revision"]["token"], "expectedContentIdentity": target["contentIdentity"], "payload": {"snapshotId": "q2", "registry": {"provider": "local", "identity": "cli-test"}}}
    command_path, config_path, result = tmp_path / "command.yaml", tmp_path / "stores.yaml", tmp_path / "result.json"
    command_path.write_text(yaml.safe_dump(command)); config_path.write_text(yaml.safe_dump({"version": "chrona/store-config/v0.1", "stores": [{"provider": "local", "identity": "cli-test", "root": str(tmp_path)}]}))
    monkeypatch.setattr(sys, "argv", ["chrona", "command-check", "--command", str(command_path), "--store-config", str(config_path), "--result", str(result)])
    main()
    assert json.loads(result.read_text(encoding="utf-8"))["status"] == "accepted"


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
        scheme = SimpleNamespace(id="same", content_identity="sha256:" + "a" * 64)
        return SimpleNamespace(
            resource=lambda kind: scheme if kind == "color-scheme" else None,
            context=SimpleNamespace(identity=SimpleNamespace(id="context")),
        )
    monkeypatch.setattr(cli, "resolve_render_context", closure)
    monkeypatch.setattr(cli, "load_yaml", lambda path: {"path": str(path)})
    monkeypatch.setattr(cli, "_run_render_review", lambda args: pytest.fail("render must not run"))
    args = cli.argparse.Namespace(context_reference=["one.yaml", "two.yaml"], snapshot_root=str(tmp_path), store_identity="test", require_content_identity=False, output_directory=str(tmp_path / "gallery"))
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
    project = yaml.safe_load((root / "examples/controller-z/project.yaml").read_text(encoding="utf-8"))
    view = yaml.safe_load((root / "examples/controller-z/views/executive.yaml").read_text(encoding="utf-8"))
    actual = yaml.safe_load((root / "examples/controller-z/actual.yaml").read_text(encoding="utf-8"))
    theme = yaml.safe_load((root / "examples/controller-z/themes/executive-light.yaml").read_text(encoding="utf-8"))
    scheme_path = root / "examples/controller-z/schemes/executive-light.yaml"
    scheme_payload = scheme_path.read_bytes()
    scheme = yaml.safe_load(scheme_payload)
    layout = yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    refs = {
        "project": _snapshot_resource(tmp_path, token, "project.yaml", project, "project", project["project"]["id"]),
        "view": _snapshot_resource(tmp_path, token, "view.yaml", view, "view", view["id"]),
        "actual": _snapshot_resource(tmp_path, token, "actual.yaml", actual, "actual-set", actual["id"]),
        "theme": _snapshot_resource(tmp_path, token, "theme.yaml", theme, "theme", theme["id"]),
        # The materializer preserves authored resource bytes.  Category bindings
        # are content-identity keyed, so parity must use the same Scheme bytes.
        "colorScheme": _snapshot_resource(tmp_path, token, "scheme.yaml", scheme, "color-scheme", scheme["id"], payload=scheme_payload),
        "layout": _snapshot_resource(tmp_path, token, "layout.yaml", layout, "layout-profile", layout["id"]),
    }
    font_root = root / "src/chrona/resources"
    font_assets = []
    for weight, name, face in ((400, "noto-sans-regular-v1.json", "regular"), (700, "noto-sans-bold-v1.json", "bold")):
        metrics_payload = (font_root / "font_metrics" / name).read_bytes()
        metrics_path = snapshot_directory(tmp_path, token) / "font_metrics" / name
        metrics_path.parent.mkdir(parents=True, exist_ok=True); metrics_path.write_bytes(metrics_payload)
        font_payload = (font_root / "fonts" / f"noto-sans-{face}-v1.ttf").read_bytes()
        font_path = snapshot_directory(tmp_path, token) / "fonts" / f"noto-sans-{face}-v1.ttf"
        font_path.parent.mkdir(parents=True, exist_ok=True); font_path.write_bytes(font_payload)
        font_assets.append({"family": "Noto Sans", "weight": weight,
                            "metrics": {"locator": {"provider": "context", "address": f"font_metrics/{name}"}, "contentIdentity": "sha256:" + sha256(metrics_payload).hexdigest()},
                            "font": {"locator": {"provider": "context", "address": f"fonts/noto-sans-{face}-v1.ttf"}, "contentIdentity": "sha256:" + sha256(font_payload).hexdigest()}})
    context = {
        "version": "chrona/render-context/v0.14", "kind": "render-context", "id": "controller-z-current",
        "body": {
            "project": refs["project"], "view": refs["view"], "theme": refs["theme"], "colorScheme": refs["colorScheme"], "layout": refs["layout"],
            "inputs": {"actual": refs["actual"]},
            "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US", "fontMetrics": {"algorithm": "declared-metrics-v2", "assets": font_assets, "missingFont": "diagnose"}, "scenePrecision": 3},
            "target": {"kind": "svg", "visualProfile": "chrona-output/visual/v0.5-baseline", "capabilities": sorted([
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

    draft_output = tmp_path / "draft.svg"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/executive.yaml"),
        "--theme", str(root / "examples/controller-z/themes/executive-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "conformance/layout-profile-intent-v0.2.yaml"),
        "--actual", str(root / "examples/controller-z/actual.yaml"), "--output", str(draft_output),
    ])
    main()
    assert draft_output.read_text(encoding="utf-8") == rendered


def test_cli_draft_render_rejects_invalid_viewport(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", "project.yaml", "--view", "view.yaml", "--theme", "theme.yaml",
        "--scheme", "scheme.yaml", "--layout", "layout.yaml", "--viewport", "wide", "--output", "out.svg",
    ])
    with pytest.raises(SystemExit) as exited:
        main()
    assert exited.value.code == 2
    assert json.loads(capsys.readouterr().out)["diagnostics"][0]["code"] == "E_COMMAND_VIEWPORT"


def test_cli_materializes_through_the_authoring_command_use_case(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace.yaml"
    command = tmp_path / "command.yaml"
    result = tmp_path / "result.json"
    command.write_text(yaml.safe_dump({
        "version": "chrona/authoring-command/v0.1", "commandId": "eject", "type": "materializePresentationPreset",
        "target": {"kind": "authoring-workspace", "path": workspace.name},
        "baseRevision": "sha256:" + "0" * 64, "payload": {"directory": "ejected"},
    }), encoding="utf-8")
    called = {}
    monkeypatch.setattr(cli, "apply_authoring_command", lambda *args, **kwargs: called.update(args=args, kwargs=kwargs) or {
        "status": "accepted", "commandId": "eject", "baseRevision": "base", "resultRevision": "result", "diagnostics": [],
    })
    monkeypatch.setattr(sys, "argv", [
        "chrona", "materialize-presentation-preset", "--workspace", str(workspace), "--command", str(command), "--result", str(result),
    ])

    main()

    assert called["args"][0] == workspace
    assert called["args"][1]["type"] == "materializePresentationPreset"
    assert called["kwargs"]["cas_write_aggregate"] is cli.cas_write_authoring_aggregate
    assert json.loads(result.read_text(encoding="utf-8"))["status"] == "accepted"


@pytest.mark.parametrize(("format_name", "prefix"), [("png", b"\x89PNG\r\n\x1a\n"), ("pdf", b"%PDF-")])
def test_cli_draft_render_writes_declared_binary_format(tmp_path, monkeypatch, format_name, prefix):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    output = tmp_path / f"review.{format_name}"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(root / "examples/controller-z/project.yaml"),
        "--view", str(root / "examples/controller-z/views/executive.yaml"),
        "--theme", str(root / "examples/controller-z/themes/executive-light.yaml"),
        "--scheme", str(root / "examples/controller-z/schemes/executive-light.yaml"),
        "--layout", str(root / "conformance/layout-profile-intent-v0.2.yaml"),
        "--actual", str(root / "examples/controller-z/actual.yaml"),
        "--format", format_name, "--output", str(output),
    ])
    main()
    assert output.read_bytes().startswith(prefix)


def test_cli_immutable_format_assertion_does_not_write_on_mismatch(tmp_path, monkeypatch, capsys):
    closure = SimpleNamespace(context=SimpleNamespace(target=SimpleNamespace(kind="svg")))
    with pytest.raises(CliFailure, match="E_RENDER_FORMAT_CONTEXT"):
        cli._assert_context_format(closure, "png")
    assert not (tmp_path / "out.svg").exists()
