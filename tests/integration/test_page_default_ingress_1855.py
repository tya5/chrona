"""Named Layout page defaults survive Draft, CLI, and guided SVG ingress (#1855)."""
from datetime import date
from pathlib import Path
from struct import unpack
import sys
from xml.etree import ElementTree

import yaml

from chrona.app.cli import main
from chrona.usecases.authoring_workspace import create_workspace
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.guided_render import WorkspaceRenderRequest, render_workspace
from tests.support import synthetic_review as sr


def _write_bundle(directory: Path, *, page_size="a4-landscape"):
    parts = sr.bundle()
    parts["layout"]["pageSize"] = page_size
    paths = {kind: sr._write(directory / f"{kind}.yaml", value)
             for kind, value in parts.items()}
    project = sr._write(directory / "project.yaml", sr.project({
        "task": sr.span("task", date(2026, 1, 5), 3, title="Short task"),
    }))
    return project, paths


def _dimensions(svg_bytes):
    root = ElementTree.fromstring(svg_bytes)
    assert root.tag.endswith("svg")
    return root.attrib["width"], root.attrib["height"], root.attrib["viewBox"]


def test_omitted_page_default_reaches_draft_svg_and_cli_file(tmp_path, monkeypatch, capsys):
    project, paths = _write_bundle(tmp_path)
    request = DraftRenderRequest(
        project=project, target_kind="svg", view=paths["view"], theme=paths["theme"],
        scheme=paths["scheme"], layout=paths["layout"],
    )

    draft = render_draft(request)
    assert _dimensions(draft.artifact.content) == ("1123", "794", "0 0 1123 794")

    output = tmp_path / "cli.svg"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(project), "--view", str(paths["view"]),
        "--theme", str(paths["theme"]), "--scheme", str(paths["scheme"]),
        "--layout", str(paths["layout"]), "--output", str(output),
    ])
    main()
    assert _dimensions(output.read_bytes()) == ("1123", "794", "0 0 1123 794")
    assert yaml.safe_load(capsys.readouterr().out)["status"] == "ok"


def test_explicit_fixed_and_auto_viewports_override_page_default_as_a_whole(tmp_path):
    project, paths = _write_bundle(tmp_path)
    common = dict(project=project, target_kind="svg", view=paths["view"], theme=paths["theme"],
                  scheme=paths["scheme"], layout=paths["layout"])

    fixed = render_draft(DraftRenderRequest(**common, viewport="900x600"))
    automatic = render_draft(DraftRenderRequest(**common, viewport="1200xauto"))

    assert _dimensions(fixed.artifact.content) == ("900", "600", "0 0 900 600")
    width, height, view_box = _dimensions(automatic.artifact.content)
    assert width == "1200"
    assert height not in {"794", "900"}  # auto content extent, not the named page's block axis
    assert view_box == f"0 0 1200 {height}"


def test_omitted_page_default_reaches_png_pixel_dimensions(tmp_path):
    project, paths = _write_bundle(tmp_path)
    rendered = render_draft(DraftRenderRequest(
        project=project, target_kind="png", view=paths["view"], theme=paths["theme"],
        scheme=paths["scheme"], layout=paths["layout"],
    ))
    assert rendered.artifact.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert unpack(">II", rendered.artifact.content[16:24]) == (1123, 794)


def _publish(directory: Path, files: dict[str, bytes]) -> None:
    directory.mkdir()
    for name, payload in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def test_omitted_guided_page_default_reaches_svg(tmp_path):
    created = create_workspace(
        tmp_path / "guided",
        {"id": "page-default", "tasks": [{
            "id": "task", "title": "Short task",
            "planned": {"start": "2026-01-05", "finish": "2026-01-08"},
        }]},
        "chrona-default-draft", publish=_publish,
    )
    preset_path = created.workspace.parent / "preset" / "preset.yaml"
    preset = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
    layout_path = created.workspace.parent / "preset" / preset["body"]["resources"]["layout"]["path"]
    layout = yaml.safe_load(layout_path.read_text(encoding="utf-8"))
    layout["pageSize"] = "a4-landscape"
    layout_path.write_text(yaml.safe_dump(layout, sort_keys=False), encoding="utf-8")

    result = render_workspace(WorkspaceRenderRequest(created.workspace, "svg"))

    assert _dimensions(result.artifact.content) == ("1123", "794", "0 0 1123 794")
