"""Scene and SVG evidence for the #1936 View controls."""
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import pytest

from tests.support import synthetic_review as sr


def _svg_member_labels(review):
    root = ElementTree.fromstring(review.artifact.content)
    return ["".join(node.itertext()) for node in root.iter()
            if node.attrib.get("data-purpose") == "member-label"]


def _ghost_render(tmp_path: Path, baseline_labels: str):
    tmp_path.mkdir(parents=True, exist_ok=True)
    current = sr.project({"work": sr.span("work", date(2026, 1, 5), 7, title="Primary task")})
    snapshot = sr.project({"work": sr.span("work", date(2026, 1, 6), 8, title="Snapshot task")})
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["comparison"].update(baseline="snapshot", baselineMarks="ghost",
                              baselineLabels=baseline_labels)
    body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress"}
    return sr.render(tmp_path, current, presentation=parts, snapshot_project=snapshot,
                     viewport=(1600, 900))


def test_baseline_labels_none_retains_ghost_mark_and_primary_label_in_scene_and_svg(tmp_path):
    automatic = _ghost_render(tmp_path / "automatic", "auto")
    hidden = _ghost_render(tmp_path / "none", "none")

    automatic_labels = [item.text for item in automatic.surface.primitives if item.purpose == "member-label"]
    scene_labels = [item.text for item in hidden.surface.primitives if item.purpose == "member-label"]
    assert set(automatic_labels) == {"Primary task", "Snapshot task"}
    assert scene_labels == ["Primary task"]
    assert _svg_member_labels(automatic) == automatic_labels
    assert _svg_member_labels(hidden) == scene_labels
    assert sum(item.purpose == "snapshot" for item in hidden.surface.primitives) == 1
    assert 'data-purpose="snapshot"' in hidden.artifact.content.decode("utf-8")


def _delta_render(tmp_path: Path, *, mode: str, omit: bool, content=("title", "finishDelta")):
    source = sr.project({
        "ontime": sr.span("ontime", date(2026, 1, 2), 8, title="On time"),
        "late": sr.span("late", date(2026, 2, 2), 8, title="Late"),
        "missing": sr.span("missing", date(2026, 3, 2), 8, title="Missing"),
    })
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
        "asOf": "2026-04-30", "observations": [
            {"id": "ontime", "sequence": 1, "projectObjectId": "ontime",
             "actual": {"start": "2026-01-02", "finish": "2026-01-10", "progress": 1}},
            {"id": "late", "sequence": 1, "projectObjectId": "late",
             "actual": {"start": "2026-02-02", "finish": "2026-02-14", "progress": 1}},
        ]}}
    parts = sr.bundle()
    body = parts["view"]["body"]
    if mode == "lanes":
        body.pop("tableColumns", None)
        body["rows"] = {"mode": "lanes", "packing": ["explicit", "attached", "chain", "dates"],
                        "laneTable": {"label": "group", "count": True}}
    else:
        body["rows"] = {"mode": "automatic"}
    body["comparison"].update(baseline="primary", facets=["planned", "actual", "finishDelta"])
    body["visibility"]["labels"] = {
        "placement": "plot", "content": list(content), "side": "end",
        "overflow": "suppress", "omitZeroDelta": omit}
    return sr.render(tmp_path, source, presentation=parts, actual=actual, viewport=(1600, 900))


@pytest.mark.parametrize("mode", ["automatic", "lanes"])
def test_plot_zero_omission_keeps_name_and_nonzero_or_missing_states_in_scene_and_svg(tmp_path, mode):
    rendered = _delta_render(tmp_path, mode=mode, omit=True)
    labels = [item.text for item in rendered.surface.primitives if item.purpose == "member-label"]
    assert set(labels) == {"On time", "Late +4d", "Missing"}
    assert _svg_member_labels(rendered) == labels


def test_plot_zero_delta_remains_opt_in(tmp_path):
    rendered = _delta_render(tmp_path, mode="automatic", omit=False)
    labels = [item.text for item in rendered.surface.primitives if item.purpose == "member-label"]
    assert "On time +0d" in labels
    assert _svg_member_labels(rendered) == labels


def test_delta_only_zero_has_no_text_while_nonzero_still_renders(tmp_path):
    rendered = _delta_render(tmp_path, mode="automatic", omit=True, content=("finishDelta",))
    labels = [item for item in rendered.surface.primitives if item.purpose == "member-label"]
    assert [(item.source_ref, item.text) for item in labels] == [("late", "+4d")]
    assert _svg_member_labels(rendered) == ["+4d"]


def _attached_render(tmp_path: Path, *, actual_at: str | None, omit: bool):
    source = sr.project({
        "campaign": sr.span("campaign", date(2026, 1, 1), 20, title="Launch campaign"),
        "gate": sr.point("gate", date(2026, 1, 10), title="Review gate"),
    })
    source["objects"]["gate"]["attachesTo"] = "campaign"
    actual = None
    if actual_at is not None:
        actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
            "asOf": "2026-01-15", "observations": [{
                "id": "gate", "sequence": 1, "projectObjectId": "gate", "actual": {"at": actual_at}}]}}
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic", "points": "attached"}
    body["comparison"].update(baseline="primary", facets=["planned", "actual", "atDelta"])
    body["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "end", "overflow": "suppress",
        "omitZeroDelta": omit}
    return sr.render(tmp_path, source, presentation=parts, actual=actual, viewport=(1600, 900))


@pytest.mark.parametrize(("actual_at", "omit", "expected"), [
    ("2026-01-10", True, "Review gate · 10 Jan"),
    ("2026-01-11", True, "Review gate · 10 Jan · +1d"),
    (None, True, "Review gate · 10 Jan"),
    ("2026-01-10", False, "Review gate · 10 Jan · +0d"),
])
def test_attached_point_zero_delta_omits_only_delta_and_keeps_required_title_date(
        tmp_path, actual_at, omit, expected):
    rendered = _attached_render(tmp_path, actual_at=actual_at, omit=omit)
    labels = [item.text for item in rendered.surface.primitives
              if item.purpose == "member-label" and item.source_ref == "gate"]
    assert labels == [expected]
    assert _svg_member_labels(rendered) == labels


def test_table_zero_omit_removes_display_affixes_but_keeps_other_cells_in_scene_and_svg(tmp_path):
    source = sr.project({
        "ontime": sr.span("ontime", date(2026, 1, 2), 8, title="On time"),
        "late": sr.span("late", date(2026, 2, 2), 8, title="Late"),
        "missing": sr.span("missing", date(2026, 3, 2), 8, title="Missing"),
    })
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
        "asOf": "2026-04-30", "observations": [
            {"id": "ontime", "sequence": 1, "projectObjectId": "ontime",
             "actual": {"start": "2026-01-02", "finish": "2026-01-10", "progress": 1}},
            {"id": "late", "sequence": 1, "projectObjectId": "late",
             "actual": {"start": "2026-02-02", "finish": "2026-02-14", "progress": 1}},
        ]}}
    parts = sr.bundle()
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic"}
    body["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays",
         "missing": "blank", "zero": "omit", "align": "end", "width": "content",
         "headerOrientation": "horizontal", "affixes": {
             "onTime": {"prefix": "(", "suffix": ")"}, "slip": {"suffix": "!"}}},
    ]
    body["visibility"]["labels"]["omitZeroDelta"] = True
    rendered = sr.render(tmp_path, source, presentation=parts, actual=actual, viewport=(1600, 900))
    cells = {item.source_ref: item.text for item in rendered.surface.primitives
             if item.purpose == "table-cell" and item.table_column_id == "Delta"}
    assert cells == {"ontime": "", "late": "+4d!", "missing": ""}
    svg_text = "".join(ElementTree.fromstring(rendered.artifact.content).itertext())
    assert "+4d!" in svg_text and "(+0d)" not in svg_text and "+0d" not in svg_text
