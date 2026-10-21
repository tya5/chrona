"""Role-bound field grouping on a Project with parent groups: order, row names, points, summaries (#1870 row 4).

Specification 06 section 6.2 "Role-bound grouping with parent groups" (R1-R4). The Projects are synthetic.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.model.info_diagnostics import FieldGroupingSummariesOmitted
from tests.integration.test_ja_jp_builtin_wording import _font_descriptor
from tests.support import synthetic_review as sr

ROLE = {"by": {"fieldRole": "responsible"}, "fallback": "hierarchy", "missing": "Unassigned", "presentation": "header"}


def _parent(key: str, stream: str | None, title: str) -> dict:
    value = {"type": "group", "title": title, "schedule": {"mode": "rollup"}}
    if stream is not None:
        value["fields"] = {"stream": stream}
    return value


def _child(key: str, parent: str, stream: str | None, start: date, title: str) -> dict:
    value = {**sr.span(key, start, 5, title=title), "parent": parent}
    value["fields"] = {"stream": stream} if stream is not None else {}
    return value


def _source(*, names=("Platform", "Mobile", "Data"), gate: dict | None = None, loose: bool = False,
            split: bool = False) -> dict:
    """Parent groups declared in the order `names`; every child carries the parent's stream.

    The alphabetical, declared and earliest-start orders differ. `split` moves one `Data` child under the
    `Platform` parent, so that parent's children span two headers.
    """
    objects: dict = {}
    for index, name in enumerate(names):
        key = name.lower()
        objects[key] = _parent(key, name, name)
        objects[f"{key}-a"] = _child(f"{key}-a", key, name, date(2026, 3 - index, 2), f"{name} design")
        objects[f"{key}-b"] = _child(f"{key}-b", key, name, date(2026, 3 - index, 9), f"{name} build")
    if split:
        objects[f"{names[0].lower()}-c"] = _child("c", names[0].lower(), names[-1], date(2026, 4, 1), "Cross-team work")
    if loose:
        objects["extras"] = _parent("extras", None, "Extras")
        objects["extras-a"] = _child("extras-a", "extras", None, date(2026, 5, 4), "Loose work")
    objects["gate"] = gate or {"type": "gate", "title": "Launch gate",
                               "schedule": {"mode": "fixed-point", "at": "2026-06-01"}}
    source = sr.project(objects, responsible_field_role=False)
    source["fieldRoles"] = {"responsible": "stream"}
    return source


def _render(tmp_path, source, *, grouping=None, rows=None, locale="en-US", columns=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["selection"]["exclude"]["objectTypes"] = []
    body["grouping"] = grouping or dict(ROLE)
    body["rows"] = {"mode": "automatic", **(rows or {})}
    if columns:
        body["tableColumns"] = [{"id": "Task", "header": "Task", "source": "path", "missing": "em-dash",
                                 "align": "start", "width": "content", "headerOrientation": "horizontal"}]
    options = {"font_metrics_path": _font_descriptor(tmp_path)} if locale == "ja-JP" else {}
    return sr.render(tmp_path, source, presentation=parts, locale=locale, **options)


def _texts(rendered, purpose):
    return [item.text for item in rendered.surface.primitives if item.kind == "Text" and item.purpose == purpose]


def _summaries(rendered):
    return [item for item in rendered.info_diagnostics if isinstance(item, FieldGroupingSummariesOmitted)]


def test_r1_headers_follow_the_declared_object_order_with_unassigned_last(tmp_path):
    rendered = _render(tmp_path, _source())

    assert _texts(rendered, "group-header") == ["Platform", "Mobile", "Data", "Unassigned"]


def test_r1_the_declared_order_is_the_projects_not_the_spelling(tmp_path):
    rendered = _render(tmp_path, _source(names=("Zeta", "Alpha", "Mid")))

    assert _texts(rendered, "group-header") == ["Zeta", "Alpha", "Mid", "Unassigned"]


def test_r1_explicit_order_and_earliest_start_take_precedence(tmp_path):
    explicit = _render(tmp_path / "explicit", _source(), grouping={**ROLE, "order": ["Data", "Platform"]})
    earliest = _render(tmp_path / "earliest", _source(), grouping={**ROLE, "order": {"by": "earliestPlannedStart"}})

    # An explicit order places an unlisted header after the listed ones, the missing group included.
    assert _texts(explicit, "group-header")[:2] == ["Data", "Platform"]
    # Data starts first (March - 2), and the missing group is last although the gate is the latest object.
    assert _texts(earliest, "group-header") == ["Data", "Mobile", "Platform", "Unassigned"]


def test_r1_unassigned_is_last_even_when_its_objects_start_first(tmp_path):
    source = _source(gate={"type": "gate", "title": "Kickoff", "schedule": {"mode": "fixed-point", "at": "2025-01-06"}})
    earliest = _render(tmp_path / "earliest", source, grouping={**ROLE, "order": {"by": "earliestPlannedStart"}})
    declared = _render(tmp_path / "declared", source)

    assert _texts(earliest, "group-header")[-1] == "Unassigned"
    assert _texts(declared, "group-header")[-1] == "Unassigned"


def test_r1_a_direct_field_grouping_stays_alphabetical(tmp_path):
    rendered = _render(tmp_path, _source(), grouping={
        "by": "field", "field": "stream", "missing": "Unassigned", "presentation": "header"})

    assert _texts(rendered, "group-header") == ["Data", "Mobile", "Platform", "Unassigned"]


@pytest.mark.parametrize("presentation", ["header", "band"])
def test_r2_a_row_name_does_not_repeat_its_header(tmp_path, presentation):
    rendered = _render(tmp_path, _source(loose=True), grouping={**ROLE, "presentation": presentation})

    names = _texts(rendered, "member-label")
    assert {"Platform design", "Mobile build", "Data design"} <= set(names)
    assert not [name for name in names if name.startswith(("Platform /", "Mobile /", "Data /"))]
    # The missing group names nothing of the path: its full path stays.
    assert "Extras / Loose work" in names
    assert "Launch gate" in names


def test_r2_a_path_column_drops_the_repeated_header_too(tmp_path):
    rendered = _render(tmp_path, _source(loose=True), columns=True)

    cells = [item.text for item in rendered.surface.primitives if item.kind == "Text"]
    assert "Platform design" in cells and "Extras / Loose work" in cells
    assert not [text for text in cells if text.startswith("Platform /")]


def test_r2_a_header_spelled_differently_does_not_cover_the_segment(tmp_path):
    source = _source()
    source["objects"]["platform"]["title"] = "Platform team"
    rendered = _render(tmp_path, source)

    names = _texts(rendered, "member-label")
    assert "Platform team / Platform design" in names
    assert "Mobile build" in names


def test_r2_the_same_rule_holds_in_ja_jp(tmp_path):
    source = _source(names=("基盤", "モバイル", "データ"))
    rendered = _render(tmp_path, source, locale="ja-JP")

    assert _texts(rendered, "group-header")[:3] == ["基盤", "モバイル", "データ"]
    names = _texts(rendered, "member-label")
    assert "基盤 design" in names
    assert not [name for name in names if name.startswith("基盤 /")]


def test_r3_a_gate_without_the_value_follows_the_key_row(tmp_path):
    rendered = _render(tmp_path, _source(), rows={"points": "key-row", "keyRow": {"title": "Key dates"}})

    assert _texts(rendered, "group-header") == ["Platform", "Mobile", "Data"]
    assert "Launch gate" in _texts(rendered, "member-label")


def test_r3_a_point_attached_to_a_task_joins_that_tasks_header(tmp_path):
    gate = {"type": "gate", "title": "Mobile review", "attachesTo": "mobile-a",
            "schedule": {"mode": "fixed-point", "at": "2026-06-01"}}
    rendered = _render(tmp_path / "header", _source(gate=gate), rows={"points": "group-header"})
    own = _render(tmp_path / "own", _source(gate=gate), rows={"points": "own-row"})

    assert _texts(rendered, "group-header") == ["Platform", "Mobile", "Data"]
    # `own-row` keeps today's behaviour: the point has its own row and no value, so it is unassigned.
    assert _texts(own, "group-header")[-1] == "Unassigned"


def test_r3_a_point_under_a_parent_group_joins_the_parents_header(tmp_path):
    gate = {"type": "gate", "title": "Data freeze", "parent": "data",
            "schedule": {"mode": "fixed-point", "at": "2026-06-01"}}
    rendered = _render(tmp_path, _source(gate=gate), rows={"points": "group-header"})

    assert _texts(rendered, "group-header") == ["Platform", "Mobile", "Data"]


def test_r4_no_info_when_each_parents_children_share_a_header(tmp_path):
    rendered = _render(tmp_path, _source())

    assert _summaries(rendered) == []


def test_r4_info_counts_the_parent_whose_children_span_two_headers(tmp_path):
    rendered = _render(tmp_path, _source(split=True))

    (info,) = _summaries(rendered)
    assert info.count == 1


def test_r4_a_gate_the_key_row_takes_out_of_the_headers_belongs_to_none(tmp_path):
    gate = {"type": "gate", "title": "Platform gate", "parent": "platform",
            "schedule": {"mode": "fixed-point", "at": "2026-06-01"}}
    keyed = _render(tmp_path / "keyed", _source(gate=gate), rows={"points": "key-row", "keyRow": {"title": "Key dates"}})
    own = _render(tmp_path / "own", _source(gate=gate), rows={"points": "own-row"})

    assert _summaries(keyed) == []
    assert [item.count for item in _summaries(own)] == [1]
