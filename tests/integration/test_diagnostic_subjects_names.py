"""Diagnostics name what the reader sees, and stay quiet when nothing is drawn (#1854 row 4)."""
from __future__ import annotations

import json
import sys
from datetime import date

from chrona.presentation.layout.surface_quality import FitWarning
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.usecases.warning_ledger import collect_render_warnings
from tests.support import synthetic_review as sr


def _thinned(tmp_path):
    source = sr.project({"a": sr.span("a", date(2027, 1, 4), 400)})
    return sr.render(tmp_path, source, viewport=(480, 400))


def _records(rendered, code):
    return [item.payload for item in rendered.warning_records if item.payload["code"] == code]


def test_axis_label_thinned_names_the_dropped_text_not_the_candidate_id(tmp_path):
    rendered = _thinned(tmp_path)
    rows = _records(rendered, "W_LAYOUT_AXIS_LABEL_THINNED")
    assert rows, "the fixture must thin at least one axis label"
    for row in rows:
        title = row["sourceTitle"]
        assert title and not title.startswith("axis-label")
        assert f"{title!r}" in row["message"]
        assert "axis-label:" not in row["message"]
        assert row["sourceRef"].startswith("/view/body/axis/tiers/")
    # the identity in the Scene diagnostics is unchanged
    assert all(row["diagnostic"].startswith("W_LAYOUT_AXIS_LABEL_THINNED:axis-label:") for row in rows)


def test_a_note_leader_fallback_names_the_note(tmp_path):
    fit = FitWarning("W_LAYOUT_ROUTE_FALLBACK", "annotation-leader:note-3", "note-3", "relation-route",
                     "direct-path", 0.0, 0.0, 400.0, 200.0,
                     subjects=(DiagnosticSubject.project_object("gate", "Design freeze"),))
    (record,) = collect_render_warnings(
        surface_diagnostics=(), tabular_warnings=(), glyph_warnings=(), fit_warnings=(fit,),
        perceptibility_warnings=(), scale_collisions=(), attachment_warnings=())
    message = record.payload["message"]
    assert "leader of note note-3" in message
    assert "relation route" not in message
    assert "'Design freeze'" in message


def test_a_relation_route_fallback_keeps_its_wording():
    fit = FitWarning("W_LAYOUT_ROUTE_FALLBACK", "link", "/relations/0", "relation-route", "direct-path",
                     0.0, 0.0, 400.0, 200.0)
    (record,) = collect_render_warnings(
        surface_diagnostics=(), tabular_warnings=(), glyph_warnings=(), fit_warnings=(fit,),
        perceptibility_warnings=(), scale_collisions=(), attachment_warnings=())
    assert record.payload["message"].startswith("a relation route fell back to a simpler path")


def _relation_policy_facts(tmp_path, *, mode, overflow="visible-overflow"):
    source = sr.project({
        "source": sr.span("source", date(2027, 1, 4), 10),
        "target": sr.span("target", date(2027, 2, 1), 10),
    }, [{"id": "link", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"}, "to": {"object": "target", "endpoint": "start"}}])
    parts = sr.bundle()
    parts["view"]["body"]["visibility"]["relations"] = {"mode": mode, "overflow": overflow}
    parts["layout"]["relationRouting"] = {"search": "first-fit", "unroutable": "relax", "maxBends": 4,
                                          "maxDetourRatio": 100}
    rendered = sr.render(tmp_path, source, presentation=parts)
    return [item for item in rendered.scene.diagnostics if item.startswith("I_LAYOUT_RELATION_POLICY_SUPERSEDED:")]


def test_relation_policy_info_is_not_emitted_when_relations_are_mode_none(tmp_path):
    assert _relation_policy_facts(tmp_path, mode="none", overflow="suppress") == []


def test_relation_policy_info_is_still_emitted_when_a_relation_is_drawn(tmp_path):
    drawn = _relation_policy_facts(tmp_path, mode="semantic", overflow="suppress")
    assert len(drawn) == 1


NOTE_PLAN = """\
version: timeline/v0.7
project:
  id: notes-demo
  title: Notes, risks and lanes
  calendar: office
fieldRoles:
  responsible: team
calendars:
  office:
    working_days: [mon, tue, wed, thu, fri]
objects:
  kickoff:
    type: gate
    title: Kickoff
    schedule: {mode: fixed-point, at: '2026-11-02'}
  design:
    type: task
    title: Design
    fields: {team: Platform}
    schedule: {mode: fixed-span, start: 2026-11-02, end: 2026-11-09}
  build:
    type: task
    title: Build
    fields: {team: Platform}
    schedule: {mode: scheduled, amount: 10wd}
  test:
    type: task
    title: Test
    fields: {team: Product}
    schedule: {mode: scheduled, amount: 5wd}
  launch:
    type: gate
    title: Launch
    schedule: {mode: scheduled-point}
relations:
- {id: design-to-build, type: dependency, from: {object: design, endpoint: end}, to: {object: build, endpoint: start}, lag: 0d}
- {id: build-to-test, type: dependency, from: {object: build, endpoint: end}, to: {object: test, endpoint: start}, lag: 0d}
- {id: test-to-launch, type: dependency, from: {object: test, endpoint: end}, to: {object: launch, endpoint: at}, lag: 0d}
annotations:
  vendor:
    kind: note
    text: Vendor confirms the build slot on 9 November.
    anchor: {object: build}
  signing:
    kind: risk
    text: Signing keys are not yet issued.
    anchor: {object: test}
"""


def test_a_real_render_names_the_note_whose_leader_fell_back(tmp_path, monkeypatch, capsys):
    from chrona.app.cli import main

    plan = tmp_path / "plan.yaml"
    plan.write_text(NOTE_PLAN, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(plan), "--preset", "target-b",
                                      "--output", str(tmp_path / "out.svg")])
    main()
    warnings = json.loads(capsys.readouterr().out)["warnings"]
    rows = [item for item in warnings if item["code"] == "W_LAYOUT_ROUTE_FALLBACK"
            and item["placementId"].startswith("annotation-leader:")]
    assert rows, "the target-b rail leader falls back for this plan"
    assert all("leader of note " in item["message"] and "relation route" not in item["message"] for item in rows)
