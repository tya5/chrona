"""Automatic rows without a title table warn when spatial names cannot fit (#1715)."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree

import pytest

from tests.support import synthetic_review as sr


TITLE_COLUMN = {
    "id": "Task",
    "source": "title",
    "missing": "em-dash",
    "align": "start",
    "width": "content",
    "headerOrientation": "horizontal",
}
WARNING_CODE = "W_LAYOUT_ROW_IDENTITY_MISSING"


def _project() -> dict:
    """Twenty-four crowded rows with uniquely identifiable, long title prefixes."""
    source = sr.bunched_project(groups=1, per_group=24)
    for index, obj in enumerate(source["objects"].values()):
        obj["title"] = f"Task {index:02} - Long descriptive objective"
    return source


def _render(tmp_path: Path, *, columns: bool, name_source: str = "title"):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic"}
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    body["visibility"]["labels"] = {
        "placement": "plot",
        "content": [name_source],
        "side": "end",
        "overflow": "suppress",
    }
    if columns:
        body["tableColumns"] = [deepcopy(TITLE_COLUMN)]
    else:
        body.pop("tableColumns", None)
    return sr.render(tmp_path, _project(), presentation=parts, viewport=(450, 600))


def _missing_member_labels(rendered) -> tuple[str, ...]:
    return tuple(
        item for item in rendered.scene.diagnostics
        if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
    )


@pytest.mark.parametrize("name_source", ("title", "path"))
def test_crowded_automatic_rows_emit_one_actionable_identity_warning(tmp_path, name_source):
    rendered = _render(tmp_path, columns=False, name_source=name_source)

    # Keep the established per-label findings. The new warning aggregates the
    # consequence of those suppressions for this automatic, table-less View.
    assert len(_missing_member_labels(rendered)) == 24
    warnings = tuple(item for item in rendered.warning_records
                     if item.payload["code"] == WARNING_CODE)
    assert len(warnings) == 1
    payload = warnings[0].payload
    assert payload["diagnostic"] == f"{WARNING_CODE}:count=24"
    assert payload["sourceRef"] == "/body/tableColumns"
    assert "24" in payload["message"]
    assert "tableColumns" in payload["message"] and "title" in payload["message"]
    assert "plot" in payload["message"] and "viewport" in payload["message"]


def test_title_column_names_all_rows_and_removes_aggregate_warning(tmp_path):
    rendered = _render(tmp_path, columns=True)

    # Labels still overflow spatially; the declared table column supplies the
    # row identities instead. The old per-label diagnostics remain unchanged.
    assert len(_missing_member_labels(rendered)) == 24
    assert not any(item.payload["code"] == WARNING_CODE for item in rendered.warning_records)

    cells = tuple(item.text for item in rendered.surface.primitives if item.purpose == "table-cell")
    assert len(cells) == 24
    assert len(set(cells)) == 24
    assert {text[:7] for text in cells} == {f"Task {index:02}" for index in range(24)}

    svg = ElementTree.fromstring(rendered.artifact.content)
    svg_text = " ".join(node.text or "" for node in svg.iter())
    assert all(text in svg_text for text in cells)
