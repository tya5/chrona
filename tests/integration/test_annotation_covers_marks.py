"""An exhausted unsafe note-box search requires an explicit safe fallback (#1869)."""
from __future__ import annotations

from pathlib import Path

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

ANCHOR = "g0-t2"


def _render(directory: Path, *, max_positions: int):
    source = sr.bunched_project(groups=4, per_group=6)
    source["annotations"] = {"n0": {"kind": "note", "text": "A note on the middle task with a few words.",
                                    "anchor": {"object": ANCHOR}}}
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    for annotation in parts["view"]["body"]["annotations"]:
        annotation["candidates"] = [sr.candidate("plot-near", connector="none", max_positions=max_positions)]
    return ak.render(directory, source, parts)


def _covered_objects(rendered) -> set[str]:
    primitives = list(rendered.surface.primitives)
    x, y, width, height = next(item for item in primitives if item.scene_id == "annotation-box:view-n0").bounds
    covered = set()
    for item in primitives:
        if not item.scene_id.startswith(("planned:", "actual:")):
            continue
        left, top, item_width, item_height = item.bounds
        if left < x + width and x < left + item_width and top < y + height and y < top + item_height:
            covered.add(item.scene_id.rsplit(":", 1)[-1])
    return covered


def test_note_box_with_a_free_placement_covers_no_other_object(tmp_path):
    rendered = _render(tmp_path, max_positions=1024)

    assert _covered_objects(rendered) <= {ANCHOR}
    assert not any(item.startswith("W_LAYOUT_ANNOTATION_COVERS_MARK") for item in rendered.scene.diagnostics)
    assert not any(item.code == "W_LAYOUT_LABEL_OVERFLOW" for item in rendered.surface.fit_warnings)


def test_exhausted_unsafe_box_requires_an_explicit_safe_fallback(tmp_path):
    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path, max_positions=1)

    assert failure.value.code == "E_LAYOUT_ANNOTATION_FALLBACK_REQUIRED"
