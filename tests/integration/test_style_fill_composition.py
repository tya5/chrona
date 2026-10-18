"""Native Style fill composition evidence from parsed rules through Layout and Scene."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from chrona.presentation.contracts.resources import ClosureIdentity, parse_contract
from chrona.presentation.layout import surface_count_closure
from chrona.presentation.layout import surface_render_plan
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.usecases import render_review as render_review_usecase
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


_ORIGINAL_COMPOSE = surface_count_closure.compose_surface_layout
_ORIGINAL_NORMALIZE = render_review_usecase.normalize_v05_surface_content
_ENCODED_COLOR = "#28c7b8"


def _style(rules):
    resource = {"version": "chrona/style/v0.2", "kind": "style", "id": "fill-composition",
                "body": {"rules": list(rules)}}
    return parse_contract(
        ClosureIdentity("style", "fill-composition", "test-v1", "sha256:" + "0" * 64), resource,
    ).rules


def _parts(*, custom_mark_role=False, duplicate_owner_columns=False):
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme.setdefault("colorScales", {})["style-owner-fill"] = {
        "slots": {"bus": "style-owner-fill"},
    }
    parts["scheme"]["body"]["categories"]["style-owner-fill"] = _ENCODED_COLOR
    if custom_mark_role:
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
        values = theme["values"]
        values["style-plan-height"] = {"type": "number", "value": 0.8}
        values["style-plan-offset"] = {"type": "number", "value": 0.1}
        theme["roles"]["style-plan"] = {
            **theme["roles"]["planned"],
            "markHeight": "style-plan-height",
            "markOffset": "style-plan-offset",
            "symbol": theme["roles"]["milestoneSymbol"]["symbol"],
        }
        for property_name in ("fill", "stroke"):
            theme["colorBindings"][f"style-plan.{property_name}"] = theme["colorBindings"][
                f"planned.{property_name}"]
    if duplicate_owner_columns:
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
        parts["view"]["body"]["tableColumns"] = [
            {"id": "Owner direct", "source": {"field": "owner"}, "missing": "em-dash",
             "align": "start", "width": "content", "headerOrientation": "horizontal"},
            {"id": "Owner via role", "source": {"fieldRole": "responsible"}, "missing": "em-dash",
             "align": "start", "width": "content", "headerOrientation": "horizontal"},
        ]
    return parts


def _text_role_without_fill(parts, role="owner-cell-emphasis"):
    body = parts["theme"]["body"]
    binding = dict(body["roles"]["text"])
    binding.pop("iconScale", None)
    binding.pop("iconGap", None)
    font_token = f"{role}-size"
    body["values"][font_token] = {"type": "number", "value": 23}
    binding["fontSize"] = font_token
    binding["contrastTreatment"] = "required"
    body["roles"][role] = binding
    assert f"{role}.fill" not in body["colorBindings"]
    return role


def _encoding(*, selector, rule_id="owner-fill"):
    return {
        "id": rule_id,
        "when": selector,
        "then": {"encode": {
            "channel": "fill", "source": {"field": "owner"},
            "scale": "style-owner-fill", "domain": "firstAppearance",
            **({"legend": {"title": "Owner"}} if "columnSource" in selector else {}),
        }},
    }


def _render(tmp_path, monkeypatch, *, source, parts, rules):
    captured = []
    normalized = []

    def compose(request, **kwargs):
        result = _ORIGINAL_COMPOSE(request, **kwargs)
        captured.append((request, result))
        return result

    def normalize(*args, **kwargs):
        kwargs["style_rules"] = rules
        kwargs.setdefault("gate_declared", "gate" in parts["theme"]["body"]["roles"])
        content = _ORIGINAL_NORMALIZE(
            *args, **kwargs,
        )
        normalized.append(content)
        return content

    monkeypatch.setattr(surface_count_closure, "compose_surface_layout", compose)
    monkeypatch.setattr(render_review_usecase, "normalize_v05_surface_content", normalize)
    directory = Path(tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    rendered = sr.render(directory, source, presentation=parts)
    assert captured
    return rendered, captured[-1][1], normalized[-1]


def _mark(rendered, source_ref):
    return next(item for item in rendered.surface.primitives
                if item.source_ref == source_ref and item.scene_id.startswith("planned:"))


def test_fill_only_rule_changes_only_matching_mark_paint(tmp_path, monkeypatch):
    parts = _parts()
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    rules = _style((_encoding(selector={"semantic": "planned"}),))
    rendered, composition, _ = _render(tmp_path / "styled", monkeypatch, source=source, parts=parts, rules=rules)

    control, _, _ = _render(tmp_path / "control", monkeypatch, source=source, parts=_parts(), rules=())
    styled_mark = _mark(rendered, "task")
    plain_mark = _mark(control, "task")
    assert styled_mark.paint.fill == _ENCODED_COLOR
    assert styled_mark.theme_role is None
    assert styled_mark.semantic_id is None
    assert styled_mark.purpose == plain_mark.purpose
    assert styled_mark.bounds == plain_mark.bounds
    assert any(mark.source_ref == "task" and mark.semantic_id == "planned"
               for mark in composition.placement.marks)


def test_role_and_fill_outcomes_compose_independently_on_same_mark(tmp_path, monkeypatch):
    parts = _parts(custom_mark_role=True)
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    rules = _style((
        {"id": "geometry-role", "when": {"semantic": "planned"},
         "then": {"role": "style-plan"}},
        _encoding(selector={"semantic": "planned"}),
    ))
    rendered, composition, _ = _render(tmp_path / "styled", monkeypatch, source=source, parts=parts, rules=rules)

    role_only_rules = _style(({"id": "geometry-role", "when": {"semantic": "planned"},
                               "then": {"role": "style-plan"}},))
    role_only, role_only_composition, _ = _render(
        tmp_path / "role-only", monkeypatch, source=source,
        parts=_parts(custom_mark_role=True), rules=role_only_rules)
    plain, plain_composition, _ = _render(
        tmp_path / "plain", monkeypatch, source=source,
        parts=_parts(custom_mark_role=True), rules=())
    mark = _mark(rendered, "task")
    role_only_mark = _mark(role_only, "task")
    layout_mark = next(item for item in composition.placement.marks
                       if item.source_ref == "task" and item.semantic_id == "planned")
    role_only_layout_mark = next(item for item in role_only_composition.placement.marks
                                 if item.source_ref == "task" and item.semantic_id == "planned")
    plain_layout_mark = next(item for item in plain_composition.placement.marks
                             if item.source_ref == "task" and item.semantic_id == "planned")
    binding = semantic_binding("planned")

    assert layout_mark.theme_role == "style-plan"
    assert layout_mark.bounds.block_size == role_only_layout_mark.bounds.block_size
    assert mark.semantic_id == "planned"
    assert mark.theme_role == "style-plan"
    assert mark.purpose == binding.purpose
    assert mark.visual_role == binding.scene_role
    assert mark.paint.fill == _ENCODED_COLOR
    assert role_only_layout_mark.bounds == layout_mark.bounds
    assert layout_mark.bounds.block_size != plain_layout_mark.bounds.block_size
    assert role_only_mark.theme_role == "style-plan"
    assert role_only_mark.paint.fill != _ENCODED_COLOR


def test_fill_only_table_cell_isolated_by_exact_column_source_for_same_object(tmp_path, monkeypatch):
    parts = _parts(duplicate_owner_columns=True)
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    rules = _style((_encoding(
        selector={"purpose": "table-cell", "columnSource": {"field": "owner"}},
        rule_id="direct-owner-column-fill",
    ),))
    rendered, composition, content = _render(tmp_path, monkeypatch, source=source, parts=parts, rules=rules)

    cells = [item for item in rendered.surface.primitives if item.purpose == "table-cell"
             and item.source_ref == "task"]
    by_column = {item.table_column_id: item for item in cells}
    assert set(by_column) == {"Owner direct", "Owner via role"}
    assert by_column["Owner direct"].paint.fill == _ENCODED_COLOR
    assert by_column["Owner direct"].semantic_id is None
    assert by_column["Owner direct"].theme_role is None
    assert by_column["Owner via role"].paint.fill != _ENCODED_COLOR
    content_by_column = {cell.column_id: cell for cell in content.table_cells if cell.object_id == "task"}
    direct_key = content_by_column["Owner direct"].style_key
    role_key = content_by_column["Owner via role"].style_key
    assert direct_key is not None and role_key is not None
    assert direct_key.subject_id == role_key.subject_id == "task"
    assert direct_key.semantic_id == role_key.semantic_id == "tableCell"
    assert direct_key.column_id == "Owner direct"
    assert role_key.column_id == "Owner via role"
    assert direct_key != role_key


def test_role_plus_fill_composes_on_text_role_without_theme_fill_binding(tmp_path, monkeypatch):
    parts = _parts(duplicate_owner_columns=True)
    role = _text_role_without_fill(parts)
    selector = {"purpose": "table-cell", "columnSource": {"field": "owner"}}
    rules = _style((
        {"id": "owner-cell-role", "when": selector, "then": {"role": role}},
        _encoding(selector=selector, rule_id="owner-cell-fill"),
    ))
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    rendered, _, _ = _render(tmp_path, monkeypatch, source=source, parts=parts, rules=rules)

    direct = next(item for item in rendered.surface.primitives
                  if item.purpose == "table-cell" and item.source_ref == "task"
                  and item.table_column_id == "Owner direct")
    other = next(item for item in rendered.surface.primitives
                 if item.purpose == "table-cell" and item.source_ref == "task"
                 and item.table_column_id == "Owner via role")
    assert direct.semantic_id == "tableCell"
    assert direct.theme_role == role
    assert direct.paint.fill == _ENCODED_COLOR
    assert direct.text_layout.font_size == 23
    assert other.theme_role is None
    assert other.paint.fill != _ENCODED_COLOR


def test_selected_table_text_role_without_binding_or_encoded_fill_fails_before_sizing(tmp_path, monkeypatch):
    parts = _parts(duplicate_owner_columns=True)
    role = _text_role_without_fill(parts, "owner-cell-no-fill")
    rules = _style(({
        "id": "owner-cell-role", "when": {"purpose": "table-cell",
                                            "columnSource": {"field": "owner"}},
        "then": {"role": role},
    },))
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 10, owner="bus")})
    measured_sources = []
    original_sources = surface_render_plan.surface_source_inputs

    def capture_sources(*args, **kwargs):
        measured_sources.append(args)
        return original_sources(*args, **kwargs)

    monkeypatch.setattr(surface_render_plan, "surface_source_inputs", capture_sources)
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, monkeypatch, source=source, parts=parts, rules=rules)

    assert caught.value.args[0] == "E_STYLE_ROLE_INCOMPATIBLE"
    assert not measured_sources
