"""Synthetic Layout evidence for Style-selected mark geometry before completion."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrenceKind, build_item_mark_visibility_index,
)
from chrona.presentation.model.mark_semantics import canonical_mark_semantic
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.usecases import render_review as render_review_usecase
from chrona.presentation.layout import surface_count_closure
from tests.support import synthetic_review as sr


_ORIGINAL_COMPOSE_SURFACE_LAYOUT = surface_count_closure.compose_surface_layout
_ORIGINAL_NORMALIZE_V05_SURFACE_CONTENT = render_review_usecase.normalize_v05_surface_content


STYLE = {
    "version": "chrona/style/v0.2",
    "kind": "style",
    "id": "synthetic-style",
    "body": {"rules": [
        {"id": "planned-geometry", "when": {"semantic": "planned"},
         "then": {"role": "style-plan"}},
        {"id": "gate-geometry", "when": {"semantic": "gate"},
         "then": {"role": "style-plan"}},
    ]},
}


def _styled_parts():
    parts = sr.bundle()
    body = parts["theme"]["body"]
    values = body["values"]
    values["style-plan-height"] = {"type": "number", "value": 0.8}
    values["style-plan-offset"] = {"type": "number", "value": 0.1}
    roles = body["roles"]
    roles["style-plan"] = {
        **roles["planned"],
        "markHeight": "style-plan-height",
        "markOffset": "style-plan-offset",
        "symbol": roles["milestoneSymbol"]["symbol"],
    }
    for property_name in ("fill", "stroke"):
        body["colorBindings"][f"style-plan.{property_name}"] = body["colorBindings"][
            f"planned.{property_name}"]
    style_contract = parse_contract(
        ClosureIdentity("style", "synthetic-style", "test-v1", "sha256:" + "0" * 64),
        STYLE,
    )
    return parts, style_contract.rules


def _source_for(mode: str):
    if mode == "ordinary":
        return sr.project({"task": sr.span("task", date(2026, 1, 5), 10)})
    if mode == "lane":
        return sr.project({"task": sr.span("task", date(2026, 1, 5), 10)})
    if mode == "folded":
        source = sr.project({"gate": sr.point("gate", date(2026, 1, 12), title="Gate")})
        source["entities"]["a"]["title"] = "Team A"
        return source
    raise AssertionError(mode)


def _source_keys(projection, parts):
    visibility = build_item_mark_visibility_index(projection, as_of=None)
    gate_declared = "gate" in parts["theme"]["body"]["roles"]
    source_keys = {}
    for occurrence, entry in visibility.entries.items():
        if occurrence.kind == MarkOccurrenceKind.LANE_FINAL:
            continue
        for visible in entry.facets:
            facet = visible.source
            semantic = canonical_mark_semantic(facet.semantic_id, facet.shape,
                                               gate_declared=gate_declared)
            key = occurrence.style_key(semantic)
            source_keys.setdefault(semantic, []).append(key)
    return source_keys


def _render_capture(tmp_path, monkeypatch, *, mode, parts, rules, styled):
    directory = Path(tmp_path) / mode
    directory.mkdir(parents=True, exist_ok=True)
    if mode == "ordinary":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    elif mode == "lane":
        parts["view"] = sr.lane_view(parts["view"], packing=("explicit",), table=True)
    elif mode == "folded":
        parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}

    captured = []
    def capture_compose(*args, **kwargs):
        result = _ORIGINAL_COMPOSE_SURFACE_LAYOUT(*args, **kwargs)
        captured.append(result)
        return result

    expected_keys = {}

    def normalize_with_style(*args, **kwargs):
        if not styled:
            return _ORIGINAL_NORMALIZE_V05_SURFACE_CONTENT(*args, **kwargs)
        expected_keys.update(_source_keys(args[0], parts))
        return _ORIGINAL_NORMALIZE_V05_SURFACE_CONTENT(
            *args, **kwargs, style_rules=rules,
        )

    monkeypatch.setattr(surface_count_closure, "compose_surface_layout", capture_compose)
    monkeypatch.setattr(render_review_usecase, "normalize_v05_surface_content", normalize_with_style)
    rendered = sr.render(directory, _source_for(mode), presentation=parts)
    assert captured
    return rendered, captured[-1], expected_keys


@pytest.mark.parametrize("mode", ("ordinary", "lane", "folded"))
def test_selected_mark_role_is_completed_in_layout_for_source_occurrences(tmp_path, monkeypatch, mode):
    parts, rules = _styled_parts()
    control_parts, _ = _styled_parts()
    rendered, composition, expected_keys = _render_capture(
        tmp_path, monkeypatch, mode=mode, parts=parts, rules=rules, styled=True,
    )
    control, control_composition, _ = _render_capture(
        tmp_path, monkeypatch, mode=mode, parts=control_parts, rules=rules, styled=False,
    )

    matching = [mark for mark in composition.placement.marks if mark.theme_role == "style-plan"]
    assert len(matching) == 1
    mark = matching[0]
    key = mark.style_occurrence_key
    assert key is not None
    assert key in {candidate for keys in expected_keys.values() for candidate in keys}
    assert key.source_kind == "combined"
    expected_kind = {"ordinary": "row", "lane": "lane-source", "folded": "folded"}[mode]
    assert key.occurrence_kind == expected_kind
    if mode == "ordinary":
        assert key.row_id and key.member_id == "task"
    elif mode == "lane":
        assert key.row_id and key.member_id
        # The final lane placement keeps the source-row identity, not a generated lane alias.
        assert mark.lane_row_id is not None and mark.lane_member_id is not None
    else:
        assert key.row_id and key.member_id == "gate"
        assert not any(row.row_id == key.row_id for row in composition.review_rows)

    control_marks = [candidate for candidate in control_composition.placement.marks
                     if candidate.source_ref == mark.source_ref and candidate.semantic_id == mark.semantic_id]
    assert len(control_marks) == 1
    baseline = control_marks[0]
    assert baseline.theme_role is None and baseline.style_occurrence_key is None
    theme_body = control_parts["theme"]["body"]
    values = theme_body["values"]
    base_token = theme_body["roles"]["planned"]["markHeight"]
    selected_token = theme_body["roles"]["style-plan"]["markHeight"]
    base_height = float(values[base_token]["value"])
    selected_height = float(values[selected_token]["value"])
    assert selected_height == pytest.approx(0.8)
    ratio = selected_height / base_height
    assert float(mark.bounds.block_size) == pytest.approx(float(baseline.bounds.block_size) * ratio)
    if mark.mark_shape == "point":
        assert float(mark.bounds.inline_size) == pytest.approx(float(baseline.bounds.inline_size) * ratio)
        assert float(mark.bounds.inline_size) == pytest.approx(float(mark.bounds.block_size))
        assert mark.symbol_parts
    else:
        assert float(mark.bounds.inline_size) == pytest.approx(float(baseline.bounds.inline_size))

    assert rendered.surface is not None
    projected = [primitive for primitive in rendered.surface.primitives
                 if primitive.theme_role == "style-plan"]
    assert projected
    binding = semantic_binding(key.semantic_id)
    assert all(primitive.semantic_id == key.semantic_id
               and primitive.visual_role == binding.scene_role
               and primitive.purpose == binding.purpose
               and primitive.source_ref == key.subject_id
               and primitive.paint is not None for primitive in projected)
    assert not any(primitive.theme_role is not None or primitive.semantic_id is not None
                   for primitive in control.surface.primitives)
    assert not any("W_THEME_ROLE_UNREAD" in str(item) and "style-plan" in str(item)
                   for item in rendered.surface.diagnostics)
