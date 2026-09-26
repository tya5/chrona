"""A point may attach to a span without scheduling effect (#486)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.core.attachments import attachment_warnings
from chrona.scheduling.scheduler import schedule

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
HALCYON = ROOT / "examples/halcyon-1/project.yaml"


def _project() -> dict:
    project = yaml.safe_load(HALCYON.read_text(encoding="utf-8"))
    project["objects"]["campaign-readiness"] = {
        "type": "gate", "title": "Campaign readiness review", "attachesTo": "campaign",
        "schedule": {"mode": "fixed-point", "at": "2027-10-01"},
    }
    return project


def _codes(project: dict) -> list[str]:
    return [item.id for item in schedule(project).diagnostics]


def test_attachment_changes_no_scheduled_date():
    attached = _project()
    detached = copy.deepcopy(attached)
    del detached["objects"]["campaign-readiness"]["attachesTo"]
    assert schedule(attached).ok
    assert schedule(attached).placements == schedule(detached).placements


@pytest.mark.parametrize(("edit", "code"), [
    (lambda objects: objects["campaign-readiness"].__setitem__("attachesTo", "nowhere"), "E_PROJECT_ATTACH_TARGET_UNKNOWN"),
    (lambda objects: objects["campaign-readiness"].__setitem__("attachesTo", "campaign-readiness"), "E_PROJECT_ATTACH_SELF"),
    (lambda objects: objects["campaign"].__setitem__("attachesTo", "structure"), "E_PROJECT_ATTACH_SOURCE_NOT_POINT"),
    (lambda objects: objects["campaign-readiness"].__setitem__("attachesTo", "pdr"), "E_PROJECT_ATTACH_TARGET_NOT_SPAN"),
])
def test_an_attachment_must_name_one_span_host_for_one_point(edit, code):
    project = _project()
    edit(project["objects"])
    assert code in _codes(project)


def test_a_point_outside_its_hosts_span_warns_but_schedules():
    project = _project()
    project["objects"]["campaign-readiness"]["schedule"]["at"] = "2027-12-01"
    result = schedule(project)
    assert result.ok
    warnings = attachment_warnings(project, result.placements)
    assert [(item.code, item.object_id, item.host_id) for item in warnings] == [
        ("W_PROJECT_ATTACHED_OUTSIDE_HOST", "campaign-readiness", "campaign")]
    project["objects"]["campaign-readiness"]["schedule"]["at"] = "2027-10-01"
    assert attachment_warnings(project, schedule(project).placements) == ()


def test_render_reports_the_outside_span_warning(tmp_path, monkeypatch, capsys):
    project = _project()
    project["objects"]["campaign-readiness"]["schedule"]["at"] = "2027-12-01"
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(path), "--output", str(tmp_path / "out.svg")])
    main()
    lines = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]
    assert any(line["code"] == "W_PROJECT_ATTACHED_OUTSIDE_HOST" and line["sourceRef"] == "campaign-readiness"
               for line in lines)
