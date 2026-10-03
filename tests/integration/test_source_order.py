"""`ordering.by: source` lists rows in the order the Project file declares its objects (#991), end to end.

Synthetic Project through the packaged `executive-light` bundle with automatic rows; no `examples/` input.
"""
from __future__ import annotations

from datetime import date

from tests.support import synthetic_review as sr


def _rows(tmp_path, by: str) -> list[str]:
    # Declared zeta, alpha, mid; planned in the reverse of that, and sorted by id it would be alpha, mid, zeta.
    source = sr.project({"zeta": sr.span("zeta", date(2026, 3, 2), 10, title="Zeta"),
                         "alpha": sr.span("alpha", date(2026, 2, 2), 10, title="Alpha"),
                         "mid": sr.span("mid", date(2026, 1, 5), 10, title="Mid")})
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic"}
    body["tableColumns"] = [{"id": "Task", "source": "title", "missing": "em-dash", "align": "start", "width": "content",
                             "headerOrientation": "horizontal"}]
    body["ordering"] = {"by": by, "direction": "ascending", "tieBreak": "id"}
    rendered = sr.render(tmp_path, source, presentation=parts)
    cells = [item for item in rendered.surface.primitives if item.purpose == "table-cell" and item.table_column_id == "Task"]
    return [item.text for item in sorted(cells, key=lambda item: item.bounds[1])]


def test_rows_follow_the_declaration_order_of_the_project_file(tmp_path):
    assert _rows(tmp_path, "source") == ["Zeta", "Alpha", "Mid"]


def test_the_other_keys_are_unchanged(tmp_path):
    assert _rows(tmp_path, "id") == ["Alpha", "Mid", "Zeta"]
