"""`{subjectId}` in a kind header shows the anchored object's id (#991), end to end.

Synthetic Project through the packaged `executive-light` bundle with the shared annotation-kind helpers.
"""
from __future__ import annotations

from copy import deepcopy

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _header_texts(tmp_path, title: str) -> list[str]:
    kinds = deepcopy(ak.KINDS)
    kinds["risk"]["title"] = title
    source = ak.project(("risk",))
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, kinds=kinds, bar=False, accent="start", label_fill="text")
    rendered = sr.render(tmp_path, source, presentation=parts)
    return [item.text for item in rendered.surface.primitives if item.scene_id.startswith("annotation-kind-text:")]


def test_subject_id_reads_the_object_id_and_subject_the_title(tmp_path):
    first = tmp_path / "id"
    first.mkdir()
    second = tmp_path / "title"
    second.mkdir()
    assert _header_texts(first, "{label} · {subjectId}")[0] == "RISK · t0"
    assert _header_texts(second, "{label} · {subject}")[0] == "RISK · Task 0"
