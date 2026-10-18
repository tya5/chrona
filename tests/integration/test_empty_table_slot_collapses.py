"""A table slot with no column source collapses to zero width instead of reserving a blank table (#1683)."""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr

COLUMN = {"id": "name", "source": "title", "format": "text", "missing": "blank", "align": "start",
          "width": "content", "headerOrientation": "horizontal"}


def _project(*, grouped=False):
    objects = {f"t{index}": sr.span(f"t{index}", date(2026, 1, 5 + index), 30,
                                    title=f"Synthetic task {index}") for index in range(6)}
    return sr.project(objects, responsible_field_role=grouped)


def _render(tmp_path, *, columns, grouped=False):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic"}
    body.pop("tableColumns", None)
    if not grouped:
        body["grouping"] = {**body["grouping"], "fallback": "none"}
    if columns:
        body["tableColumns"] = [dict(COLUMN)]
    return sr.render(tmp_path, _project(grouped=grouped), presentation=parts, viewport=(1200, None))


def _slot(rendered, source):
    return next(item for item in rendered.surface.slots if item.source == source)


def test_a_view_with_no_columns_leaves_no_blank_table_slot(tmp_path):
    rendered = _render(tmp_path, columns=False)
    assert float(_slot(rendered, "table").bounds[2]) == 0.0


def test_the_plot_takes_the_room_the_blank_table_would_have_held(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    empty, columned = _render(tmp_path / "a", columns=False), _render(tmp_path / "b", columns=True)
    assert float(_slot(columned, "table").bounds[2]) > 0
    assert float(_slot(empty, "timeline").bounds[2]) > float(_slot(columned, "timeline").bounds[2])


def test_group_headers_keep_the_table_slot_even_without_columns(tmp_path):
    rendered = _render(tmp_path, columns=False, grouped=True)
    assert float(_slot(rendered, "table").bounds[2]) > 0
