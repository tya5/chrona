"""Child rows indented under field-grouping headers (#1065), end to end.

Synthetic Projects grouped by owner go through the packaged `executive-light` bundle with automatic rows and one
table column; no test reads `examples/`. The committed Controller Z slide is evidence, not a gate.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.presentation import header_group_cell_indent, table_cell_indent
from chrona.presentation.review.v05_content import _indents_under_headers
from chrona.presentation.model.closure import ClosureError
from tests.support import synthetic_review as sr

COLUMN = "Work item"
OWNERS = ("bus", "payload")


def _source(title_suffix: str = "") -> dict:
    objects = {}
    for index, owner in enumerate(OWNERS):
        for number in range(2):
            key = f"t-{owner}-{number}"
            objects[key] = sr.span(key, date(2026, 1, 5) + timedelta(days=index * 20 + number * 15), 12, owner=owner,
                                   title=f"Task {owner} {number}{title_suffix}")
    source = sr.project(objects)
    for owner in OWNERS:
        source["entities"][owner]["title"] = owner.title()
    return source


def _parts(*, indent: bool = True, presentation: str | None = "header",
           preset: str = "executive-light", width: dict | None = None) -> dict:
    parts = sr.bundle(preset)
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic"}
    body["tableColumns"] = [{"id": COLUMN, "source": "title", "missing": "em-dash", "align": "start",
                             "width": width or {"minmax": {"min": "content", "max": {"fr": 1}}},
                             "headerOrientation": "horizontal"}]
    if presentation is None:
        body["grouping"].pop("presentation")
    else:
        body["grouping"]["presentation"] = presentation
    if indent:
        body["hierarchyColumn"] = COLUMN
    return parts


def _step(parts: dict) -> float:
    theme = parts["theme"]["body"]
    return float(theme["values"][theme["metrics"]["table.indent.inlineSize"]]["value"])


def _render(directory, parts, source=None, viewport=(1600, 900)):
    directory.mkdir(parents=True, exist_ok=True)
    return sr.render(directory, source or _source(), presentation=parts, viewport=viewport)


def _starts(rendered) -> dict[str, float]:
    return {item.scene_id: item.bounds[0] for item in rendered.surface.primitives
            if item.scene_id.startswith(("cell:", "group-header:"))}


def _children(starts: dict[str, float]) -> dict[str, float]:
    return {key: value for key, value in starts.items() if key.startswith("cell:")}


def _headers(starts: dict[str, float]) -> dict[str, float]:
    return {key: value for key, value in starts.items() if key.startswith("group-header:")}


def test_every_child_label_starts_exactly_one_step_after_its_header_label(tmp_path):
    parts = _parts()
    starts = _starts(_render(tmp_path, parts))
    headers, children = _headers(starts), _children(starts)
    assert len(headers) == len(OWNERS) and len(children) == 2 * len(OWNERS)
    header_start = {value for value in headers.values()}
    assert len(header_start) == 1  # one header label start for every group
    for key, start in children.items():
        assert start - next(iter(header_start)) == pytest.approx(_step(parts))  # A1


def test_header_labels_and_unindented_cells_are_unchanged(tmp_path):
    plain = _starts(_render(tmp_path / "plain", _parts(indent=False)))
    indented = _starts(_render(tmp_path / "indented", _parts()))
    assert _headers(plain) == _headers(indented)  # A2: header labels do not move
    step = _step(_parts())
    for key, start in _children(plain).items():
        assert _children(indented)[key] == pytest.approx(start + step)


def test_a_start_group_tab_leads_the_header_label_and_the_children_follow_it(tmp_path):
    parts = _parts(preset="control-room-dark")
    theme = parts["theme"]["body"]
    theme["values"]["tab.size"] = {"type": "number", "value": 6}
    theme["values"]["tab.gap"] = {"type": "number", "value": 4}
    theme["values"]["tab.opacity"] = {"type": "number", "value": 1}
    theme["roles"]["group-tab"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 20, "opacity": "tab.opacity",
                                   "tabInlineSize": "tab.size", "tabGap": "tab.gap"}
    theme["colorBindings"]["group-tab.fill"] = "accent"
    parts["theme"]["version"] = "chrona/theme/v0.13"
    starts = _starts(_render(tmp_path, parts))
    header_start = next(iter(_headers(starts).values()))
    plain_header = next(iter(_headers(_starts(_render(tmp_path / "plain", _parts(indent=False, preset="control-room-dark")))).values()))
    assert header_start - plain_header == pytest.approx(10)  # the label starts after the tab and its gap
    for start in _children(starts).values():
        assert start - header_start == pytest.approx(_step(parts))  # still exactly one step after the label


def test_a_later_hierarchy_column_is_indented_from_its_own_start_even_beside_a_tab(tmp_path):
    parts = _parts(preset="control-room-dark")
    body = parts["view"]["body"]
    body["tableColumns"].insert(0, {**body["tableColumns"][0], "id": "Code", "width": "content"})
    theme = parts["theme"]["body"]
    theme["values"]["tab.size"] = {"type": "number", "value": 6}
    theme["values"]["tab.opacity"] = {"type": "number", "value": 1}
    theme["roles"]["group-tab"] = {"backgroundTreatment": "fill", "backgroundPaintOrder": 20, "opacity": "tab.opacity",
                                   "tabInlineSize": "tab.size"}
    theme["colorBindings"]["group-tab.fill"] = "accent"
    parts["theme"]["version"] = "chrona/theme/v0.13"
    rendered = _render(tmp_path, parts)
    column_start = next(item.bounds[0] for item in rendered.surface.primitives if item.scene_id == f"column:{COLUMN}")
    cells = [item.bounds[0] for item in rendered.surface.primitives if item.scene_id.endswith(f":{COLUMN}")
             and item.scene_id.startswith("cell:")]
    assert cells and all(start - column_start == pytest.approx(_step(parts)) for start in cells)  # no tab lead here


def test_a_vertical_group_tag_draws_no_header_row_and_no_indent(tmp_path):
    parts = _parts()
    theme = parts["theme"]["body"]
    theme["values"]["writing-vertical"] = {"type": "writingMode", "value": "vertical"}
    theme["roles"]["groupHeader"]["writingMode"] = "writing-vertical"
    vertical = _starts(_render(tmp_path / "vertical", parts))
    parts_plain = deepcopy(parts)
    parts_plain["view"]["body"].pop("hierarchyColumn")
    plain = _starts(_render(tmp_path / "plain", parts_plain))
    assert _children(vertical) == _children(plain)  # rows are not below a header: nothing to indent under


def test_a_narrow_flexible_column_cuts_the_indented_label_with_its_source_kept(tmp_path):
    source = _source(" with a long and verbose title that needs room")
    texts = {}
    for name, indent in (("plain", False), ("indented", True)):
        parts = _parts(indent=indent, width={"fr": 1})
        sr.fix_inline(parts, "table", 150)
        sr.find_node(parts["layout"], "table")["overflow"] = "ellipsize-with-source"
        rendered = _render(tmp_path / name, parts, source)
        texts[name] = {item.scene_id: item.text for item in rendered.surface.primitives
                       if item.scene_id.startswith("cell:")}
    for key, plain in texts["plain"].items():
        cut = texts["indented"][key]
        assert cut.endswith("…") and len(cut) <= len(plain)  # the ladder runs inside the smaller room


def test_a_content_sized_table_is_as_wide_as_its_widest_indented_label(tmp_path):
    parts = _parts(width="content")
    sr.find_node(parts["layout"], "table")["inlineSize"] = "content"
    plain_parts = _parts(indent=False, width="content")
    sr.find_node(plain_parts["layout"], "table")["inlineSize"] = "content"
    long = _source(" with a long and verbose title that needs room")
    width = {name: next(slot.bounds[2] for slot in _render(tmp_path / name, value, long).surface.slots
                        if slot.slot_id == "table") for name, value in (("indented", parts), ("plain", plain_parts))}
    assert width["indented"] - width["plain"] == pytest.approx(_step(parts), abs=1.0)


@pytest.mark.parametrize("kwargs", [{"presentation": "band"}, {"presentation": None}])
def test_without_header_groups_the_declaration_stays_an_error(tmp_path, kwargs):
    with pytest.raises(ClosureError) as caught:
        _render(tmp_path, _parts(**kwargs))
    assert caught.value.diagnostic_id == "E_VIEW_HIERARCHY_COLUMN_UNEXPECTED"


def test_the_other_nesting_rules_are_not_replaced():
    grouping = lambda by, presentation="header": SimpleNamespace(by=by, presentation=presentation)  # noqa: E731
    rows = lambda *items: SimpleNamespace(items=items)  # noqa: E731
    row = lambda depth=0, parent=None: SimpleNamespace(depth=depth, parent_row=parent)  # noqa: E731
    view = lambda **kwargs: SimpleNamespace(hierarchy_column=kwargs.get("column", "c"), grouping=kwargs.get("grouping"),
                                             rows=kwargs.get("rows", rows()))  # noqa: E731
    assert _indents_under_headers(view(grouping=grouping("field")))
    assert _indents_under_headers(view(grouping=grouping("objectType")))
    assert not _indents_under_headers(view(grouping=grouping("hierarchy")))  # hierarchy keeps its depths
    assert not _indents_under_headers(view(grouping=grouping("field"), rows=rows(row(depth=1))))
    assert not _indents_under_headers(view(grouping=grouping("field"), rows=rows(row(parent="p"))))
    assert not _indents_under_headers(view(grouping=grouping("field", "band")))
    assert not _indents_under_headers(view(grouping=None))
    assert not _indents_under_headers(view(grouping=grouping("field"), column=None))
    # The hierarchy rule itself: the group's inset plus the step times the depth, as before.
    assert table_cell_indent(grouped=True, depth=2, inset=10.0, indent=16.0) == 42.0
    assert table_cell_indent(grouped=False, depth=0, inset=10.0, indent=None) == 0.0
    assert header_group_cell_indent(grouped=True, indent=16.0, lead=6.0) == 22.0
    assert header_group_cell_indent(grouped=True, indent=16.0, lead=None) == 0.0  # no header row is drawn
    assert header_group_cell_indent(grouped=False, indent=16.0, lead=0.0) == 0.0  # not below any header
