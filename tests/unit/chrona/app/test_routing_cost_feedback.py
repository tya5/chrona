"""A cost advisory is early feedback, not opt-in phase progress."""
from io import StringIO
import importlib
import sys

import pytest
import yaml

from chrona.app import cli
from chrona.app.agent_tools import call_tool
from chrona.app.agent_workspace import WorkspaceScope
from chrona.presentation.model.info_diagnostics import RoutingCostAdvisory
from chrona.usecases.diagnostic_messages import describe_warning, warning_message


def _project(relation_count=1):
    return {
        "version": "timeline/v0.7", "project": {"id": "cost", "title": "Cost"},
        "objects": {
            "a": {"type": "task", "title": "A", "schedule": {
                "mode": "fixed-span", "start": "2027-01-04", "end": "2027-01-05"}},
            "b": {"type": "task", "title": "B", "schedule": {
                "mode": "fixed-span", "start": "2027-01-06", "end": "2027-01-07"}},
        },
        "relations": [{"id": f"ab-{index}", "type": "dependency", "lag": "0d",
                       "from": {"object": "a", "endpoint": "end"},
                       "to": {"object": "b", "endpoint": "start"}} for index in range(relation_count)],
    }


def test_quiet_nonterminal_reports_cost_but_not_phase_progress(monkeypatch):
    stream = StringIO()
    monkeypatch.setattr(cli.sys, "stderr", stream)
    progress = cli._draft_render_progress(False)
    assert progress is not None

    progress.phase("layout")
    progress.advisory(RoutingCostAdvisory("table-timeline", 336))
    progress.phase("output")

    text = stream.getvalue()
    assert text.count("W_LAYOUT_ROUTING_COST") == 1
    assert "--relations none" in text and "relationRouting" in text
    assert "potentialPortPairs=336" in text and "surface=table-timeline" in text
    assert "chrona: layout" not in text and "chrona: output" not in text


def test_explicit_progress_preserves_phases_alongside_advisory(monkeypatch):
    stream = StringIO()
    monkeypatch.setattr(cli.sys, "stderr", stream)
    progress = cli._draft_render_progress(True)
    progress.phase("layout")
    progress.advisory(RoutingCostAdvisory("table-timeline", 336))
    progress.phase("output")
    lines = stream.getvalue().splitlines()
    assert lines[0] == "chrona: layout"
    assert "W_LAYOUT_ROUTING_COST" in lines[1]
    assert lines[2] == "chrona: output"


def test_early_and_final_warning_use_the_same_actionable_message(monkeypatch):
    stream = StringIO()
    monkeypatch.setattr(cli.sys, "stderr", stream)
    advisory = RoutingCostAdvisory("table-timeline", 336)
    cli._draft_render_progress(False).advisory(advisory)
    message = warning_message(describe_warning({
        "code": advisory.code, "diagnostic": advisory.scene_diagnostic(),
    }))
    assert stream.getvalue() == f"chrona: {advisory.code}: {message}\n"


def test_real_large_relation_input_warns_before_first_route_search(tmp_path, monkeypatch, capsys):
    source = tmp_path / "large.yaml"
    source.write_text(yaml.safe_dump(_project(336)), encoding="utf-8")
    surface_routes = importlib.import_module("chrona.presentation.layout.surface_routes")

    class BeforeExpensiveLayout(BaseException):
        pass

    def stop_before_search(*_args, **_kwargs):
        feedback = capsys.readouterr().err
        assert "W_LAYOUT_ROUTING_COST" in feedback
        assert "potentialPortPairs=" in feedback
        assert "--relations none" in feedback and "relationRouting" in feedback
        assert "chrona: layout" not in feedback
        raise BeforeExpensiveLayout

    monkeypatch.setattr(surface_routes, "select_relation_route", stop_before_search)
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(source), "-o", str(tmp_path / "plan.svg")])
    with pytest.raises(BeforeExpensiveLayout):
        cli.main()
    assert not (tmp_path / "plan.svg").exists()


def test_mcp_completed_warning_keeps_the_same_advisory_once(tmp_path, monkeypatch):
    source = tmp_path / "plan.yaml"
    source.write_text(yaml.safe_dump(_project()), encoding="utf-8")
    surface_routes = importlib.import_module("chrona.presentation.layout.surface_routes")
    advisory = RoutingCostAdvisory("table-timeline", 336)
    # Workload admission has separate synthetic fanout/boundary tests. Here
    # isolate completed warning transport from the expensive search itself.
    monkeypatch.setattr(surface_routes, "routing_cost_advisory", lambda *_args: advisory)
    result = call_tool(WorkspaceScope(tmp_path), "render_draft", {"project": "plan.yaml", "inline": "none"})
    assert result.structured["status"] == "ok", result.structured
    warnings = [item for item in result.structured["warnings"] if item["code"] == advisory.code]
    assert len(warnings) == 1
    assert "--relations none" in warnings[0]["message"] and "relationRouting" in warnings[0]["message"]
