"""Native Layout/Scene evidence for Style-selected member-label typography."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract
from chrona.presentation.layout import surface_count_closure
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.model.semantic_registry import (
    inside_member_label_semantic, semantic_binding,
)
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, StyleOccurrence, evaluate_style_rules,
)
from chrona.usecases import render_review as render_review_usecase
from tests.support import synthetic_review as sr


_ORIGINAL_COMPOSE = surface_count_closure.compose_surface_layout
_ORIGINAL_NORMALIZE = render_review_usecase.normalize_v05_surface_content

_STYLE = {
    "version": "chrona/style/v0.2",
    "kind": "style",
    "id": "synthetic-label-style",
    "body": {"rules": [
        {"id": "inside-label", "when": {"semantic": "memberLabelInsidePlanned"},
         "then": {"role": "style-inside-label"}},
        {"id": "outside-label", "when": {"semantic": "memberLabel"},
         "then": {"role": "style-outside-label"}},
    ]},
}


def _parts():
    parts = sr.bundle()
    body = parts["theme"]["body"]
    for role, size in (("style-inside-label", 26), ("style-outside-label", 17)):
        base = dict(body["roles"]["text"])
        base.pop("iconScale", None)
        base.pop("iconGap", None)
        size_token = f"{role}-size"
        body["values"][size_token] = {"type": "number", "value": size}
        base["fontSize"] = size_token
        base["contrastTreatment"] = "required"
        body["roles"][role] = base
        body["colorBindings"][f"{role}.fill"] = body["colorBindings"]["text.fill"]

    view = parts["view"]["body"]
    view["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "auto", "overflow": "visible-overflow",
    }
    view["visibility"]["fallback"] = {"labels": ["inside", "end", "suppress"]}
    contract = parse_contract(
        ClosureIdentity("style", "synthetic-label-style", "test-v1", "sha256:" + "0" * 64),
        _STYLE,
    )
    return parts, contract.rules


def _source(mode: str):
    if mode in {"ordinary", "lane"}:
        return sr.project({"task": sr.span(
            "task", date(2026, 1, 5), 10, title="Task")})
    if mode == "folded":
        source = sr.project({"gate": sr.point(
            "gate", date(2026, 1, 12), title="Task")})
        source["entities"]["a"]["title"] = "Team A"
        return source
    raise AssertionError(mode)


def _label_facts(projection):
    sources = StyleSourceOccurrences.from_projection(projection, as_of=None)
    facts = []

    def add(item, container_id, *, folded=False):
        outside = sources.label_key(item, container_id, "memberLabel", folded=folded)
        inside = replace(outside, semantic_id=inside_member_label_semantic(outside.source_kind))
        for key in (outside, inside):
            binding = semantic_binding(key.semantic_id)
            facts.append(StyleOccurrence(key, binding.purpose, binding.primitive_kind))

    if sources.lane_mode:
        for row in projection.lane_rows:
            for item in row.items:
                add(item, row.lane_id)
    else:
        for row in projection.rows:
            for item in row.items:
                add(item, row.row_id)
        for folded in projection.folded_points:
            add(folded.item, folded.group_id, folded=True)
    return tuple(facts)


def _render(tmp_path, monkeypatch, *, mode: str, styled: bool):
    parts, rules = _parts()
    if mode == "ordinary":
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    elif mode == "lane":
        parts["view"] = sr.lane_view(parts["view"], packing=("explicit",), table=True)
        parts["view"]["body"]["visibility"]["labels"] = {
            "placement": "plot", "content": ["title"], "side": "auto", "overflow": "suppress",
        }
        parts["view"]["body"]["visibility"]["fallback"] = {
            "labels": ["inside", "end", "suppress"],
        }
    elif mode == "folded":
        parts["view"]["body"]["rows"] = {
            "mode": "automatic", "points": "group-header",
        }

    captured = []

    def compose(request, **kwargs):
        result = _ORIGINAL_COMPOSE(request, **kwargs)
        captured.append((request, result))
        return result

    def normalize(*args, **kwargs):
        content = _ORIGINAL_NORMALIZE(*args, **kwargs)
        if not styled:
            return content
        facts = _label_facts(args[0])
        return replace(content, style_intents=OccurrenceStyleIndex(evaluate_style_rules(rules, facts)))

    monkeypatch.setattr(surface_count_closure, "compose_surface_layout", compose)
    monkeypatch.setattr(render_review_usecase, "normalize_v05_surface_content", normalize)
    directory = Path(tmp_path) / f"{mode}-{'styled' if styled else 'plain'}"
    directory.mkdir(parents=True, exist_ok=True)
    rendered = sr.render(directory, _source(mode), presentation=parts)
    assert captured
    return rendered, captured[-1], parts


@pytest.mark.parametrize("mode", ("ordinary", "lane", "folded"))
def test_selected_member_label_roles_reach_layout_and_scene(tmp_path, monkeypatch, mode):
    rendered, (request, composition), parts = _render(
        tmp_path, monkeypatch, mode=mode, styled=True)
    control, (_, control_composition), _ = _render(
        tmp_path, monkeypatch, mode=mode, styled=False)

    labels = [item for item in composition.placement.text if item.semantic_id == "memberLabel"
              and item.theme_role in {"style-inside-label", "style-outside-label"}]
    assert len(labels) == 1, [(item.placement_id, item.semantic_id, item.theme_role,
                               item.selected_rung) for item in composition.placement.text]
    label = labels[0]
    assert label.style_occurrence_key is not None
    assert label.style_occurrence_key.occurrence_kind == {
        "ordinary": "row", "lane": "lane-source", "folded": "folded",
    }[mode]
    expected_role = ("style-inside-label" if label.selected_rung == "inside"
                     else "style-outside-label")
    assert label.theme_role == expected_role
    if mode != "folded":
        assert "inside" in label.fallback_ladder and "end" in label.fallback_ladder
    else:
        assert label.fallback_ladder == ("end", "start")
    assert label.font_size == parts["theme"]["body"]["values"][f"{expected_role}-size"]["value"]
    expected_semantic = ("memberLabelInsidePlanned" if label.selected_rung == "inside"
                         else "memberLabel")
    assert label.style_occurrence_key.semantic_id == expected_semantic
    assert label.style_occurrence_key.subject_id in {"task", "gate"}

    if mode == "lane":
        preflight = {item.placement_id: item for item in request.fixed_lane_preflight.measured_labels}
        measured = preflight[label.placement_id]
        leaves = dict(measured.candidate_measurements)
        assert set(leaves) == {"inside", "end"}
        assert leaves["inside"].font_size != leaves["end"].font_size
        leaf = leaves[label.selected_rung]
        assert leaf.font_size == label.font_size
        assert leaf.width >= label.bounds.inline_size
        assert leaf.height >= label.bounds.block_size

    primitive = next(item for item in rendered.surface.primitives
                     if item.scene_id == label.placement_id)
    binding = semantic_binding(label.style_occurrence_key.semantic_id)
    assert primitive.semantic_id == label.style_occurrence_key.semantic_id
    assert primitive.theme_role == label.theme_role
    assert primitive.visual_role == binding.scene_role
    assert primitive.purpose == binding.purpose
    assert primitive.text_layout.font_size == label.font_size
    assert primitive.paint is not None
    assert primitive.paint.fill == request.theme_tokens.color(label.theme_role)

    plain = [item for item in control_composition.placement.text if item.semantic_id == "memberLabel"]
    assert len(plain) == 1
    assert plain[0].theme_role is None and plain[0].style_occurrence_key is None
    assert plain[0].font_size != label.font_size
    plain_scene = next(item for item in control.surface.primitives
                       if item.scene_id == plain[0].placement_id)
    assert plain_scene.theme_role is None and plain_scene.semantic_id is None
    assert not any("W_THEME_ROLE_UNREAD" in str(item) and "style-" in str(item)
                   for item in rendered.surface.diagnostics)
