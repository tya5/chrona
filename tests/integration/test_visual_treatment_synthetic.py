"""Visual-treatment omission and rich-profile paint on a synthetic project (#657, #575).

The rules -- a Theme role may ask for a treatment the baseline visual profile does not
paint (reported as `I_VISUAL_TREATMENT_OMITTED`, never a failure) and the rich profile paints
it -- do not depend on the HALCYON board.  These tests give the elevated preset a small
synthetic project, so they stay on the PR path while the two HALCYON renders in
`test_render.py` run under the `corpus` marker.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import yaml

from chrona.app.cli import _emit_render_result
from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.info_diagnostics import PaintOmission
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review
from tests.support import synthetic_review as sr

RICH = "chrona-output/visual/v0.6-svg"
BASELINE = "chrona-output/visual/v0.5-baseline"
OWNERS = ("a", "b", "c")


def _project() -> dict:
    objects = {}
    for index, owner in enumerate(OWNERS):
        for step in range(2):
            key = f"{owner}{step}"
            objects[key] = sr.span(key, date(2026, 3, 2) + timedelta(days=index * 9 + step * 50), 40, owner=owner,
                                   title=f"Synthetic task {key}")
    return sr.project(objects)


def _render(directory: Path, presentation: dict, visual_profile: str = BASELINE) -> RenderedReview:
    paths = {}
    for kind, value in presentation.items():
        paths[kind] = directory / f"{kind}.yaml"
        paths[kind].write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    project = directory / "project.yaml"
    project.write_text(yaml.safe_dump(_project(), sort_keys=False), encoding="utf-8")
    draft = resolve_draft_render(
        project_path=project, view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"],
        viewport=(1600, 900), visual_profile=visual_profile)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


def test_elevated_preset_reports_default_profile_omissions_and_rich_svg_paints_them(tmp_path, capsys):
    presentation = sr.bundle("elevated-light")
    baseline = _render(tmp_path, presentation)
    omissions = [item for item in baseline.info_diagnostics if item.code == "I_VISUAL_TREATMENT_OMITTED"]
    assert {(item.role, item.treatment, item.paintable_profile) for item in omissions} == {
        ("group-band", "linear-gradient", RICH),
        ("group-band", "drop-shadow", RICH),
    }
    assert all(item.source_ref.startswith("/body/roles/group-band/") for item in omissions)
    assert sum(item.startswith("I_VISUAL_TREATMENT_OMITTED:") for item in baseline.scene.diagnostics) == 2
    assert len([item for item in baseline.surface.primitives if item.visual_role == "group-band"]) == len(OWNERS)
    _emit_render_result(baseline)
    output = capsys.readouterr()
    assert output.err == ""
    envelope = json.loads(output.out)
    assert envelope["status"] == "ok" and envelope["diagnostics"] == []
    notices = [item for item in envelope["warnings"] if item["code"] == "I_VISUAL_TREATMENT_OMITTED"]
    assert len(notices) == 2
    assert all(item["severity"] == "info" and item["paintableProfile"] == RICH for item in notices)

    (tmp_path / "rich").mkdir()
    rich = _render(tmp_path / "rich", presentation, RICH)
    assert not any(item.startswith("I_VISUAL_TREATMENT_OMITTED:") for item in rich.scene.diagnostics)
    bands = [item for item in rich.surface.primitives if item.visual_role == "group-band"]
    assert len(bands) == len(OWNERS)
    assert all(item.paint.gradient is not None and item.paint.shadow is not None for item in bands)
    assert b"<linearGradient" in rich.artifact.content and b"<filter" in rich.artifact.content


def test_planned_mark_shadow_is_supported_but_optional_under_baseline(tmp_path):
    presentation = sr.bundle("elevated-light")
    theme = presentation["theme"]
    shadow = {key: value for key, value in theme["body"]["roles"]["group-band"].items() if key.startswith("shadow")}
    theme["body"]["roles"]["planned"].update(shadow)
    theme["body"]["colorBindings"]["planned.shadowColor"] = "neutral"
    (tmp_path / "rich").mkdir()
    baseline = _render(tmp_path, presentation)
    rich = _render(tmp_path / "rich", presentation, RICH)
    assert any(isinstance(item, PaintOmission) and item.role == "planned" and item.treatment == "drop-shadow"
               for item in baseline.info_diagnostics)
    planned = [item for item in baseline.surface.primitives if item.visual_role == "planned"]
    assert planned and all(item.paint.shadow is None for item in planned)
    rich_planned = [item for item in rich.surface.primitives if item.visual_role == "planned"]
    assert rich_planned and all(item.paint.shadow is not None for item in rich_planned)
    assert re.search(rb'<rect[^>]*data-purpose="planned"[^>]*filter="url\(#shadow-', rich.artifact.content)
