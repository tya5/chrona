"""A Theme `tableColumnLabel` text role sets the table's column headers apart from its cells (#991).

The headers shared the `text` role, so they could not be smaller, muted or letter-spaced without changing every cell.
Synthetic Project through the packaged `executive-light` bundle with automatic rows and a title and a phase column;
no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr


def _render(tmp_path, *, role: bool, fill: bool = True):
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"), "b": sr.span("b", date(2026, 3, 9), 20, title="Beta")})
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [
        {"id": "Work package", "source": "title", "missing": "em-dash", "align": "start", "width": "content", "headerOrientation": "horizontal"},
        {"id": "Owner", "source": {"field": "owner"}, "missing": "em-dash", "align": "start", "width": "content", "headerOrientation": "horizontal"}]
    if role:
        body["values"]["header-size"] = {"type": "number", "value": 9}
        body["values"]["header-spacing"] = {"type": "number", "value": 0.1}
        body["roles"]["tableColumnLabel"] = {**body["roles"]["text"], "fontSize": "header-size", "letterSpacing": "header-spacing"}
        if fill:
            body["colorBindings"]["tableColumnLabel.fill"] = "textMuted"
    return sr.render(tmp_path, source, presentation=parts)


def _header_and_cell(rendered):
    header = next(item for item in rendered.surface.primitives if item.scene_id == "column:Work package")
    cell = next(item for item in rendered.surface.primitives if item.purpose == "table-cell" and item.text == "Alpha")
    return header, cell


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_without_the_role_headers_and_cells_share_the_text_role(tmp_path):
    header, cell = _header_and_cell(_render(_sub(tmp_path, "a"), role=False))
    assert header.visual_role == "text" and header.text_layout.font_size == cell.text_layout.font_size


def test_the_role_sets_the_header_size_spacing_and_colour_apart_from_the_cells(tmp_path):
    plain_header, plain_cell = _header_and_cell(_render(_sub(tmp_path, "plain"), role=False))
    header, cell = _header_and_cell(_render(_sub(tmp_path, "role"), role=True))

    assert header.text_layout.font_size == 9 and header.text_layout.letter_spacing == pytest.approx(0.9)  # 0.1 em of 9
    assert header.visual_role == "tableColumnLabel" and header.paint.fill != plain_header.paint.fill
    assert cell.text_layout.font_size == plain_cell.text_layout.font_size  # the cells are untouched
    assert cell.paint.fill == plain_cell.paint.fill
    assert header.bounds[3] < plain_header.bounds[3]  # a smaller header is a shorter text box


def test_a_role_without_a_fill_changes_type_but_keeps_the_text_colour(tmp_path):
    plain_header, _ = _header_and_cell(_render(_sub(tmp_path, "plain"), role=False))
    header, _ = _header_and_cell(_render(_sub(tmp_path, "nofill"), role=True, fill=False))
    assert header.text_layout.font_size == 9 and header.visual_role == "text"
    assert header.paint.fill == plain_header.paint.fill
