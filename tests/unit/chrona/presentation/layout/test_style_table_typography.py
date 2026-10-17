"""Table typography is completed before source sizing and reused at placement."""
from __future__ import annotations

from dataclasses import replace

import pytest

from chrona.presentation.layout import surface_render_plan as planner
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.style_text import resolve_table_cell_typography
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex,
    OccurrenceStyleIntent,
    StyleOccurrenceKey,
)
from chrona.presentation.model.semantic_registry import (
    ContrastClass, semantic_binding, semantic_ids,
)
from chrona.presentation.model.surface_content import TableCellContent
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.usecases import render_review as usecase
from tests.support import synthetic_review as sr


def _intent(key: StyleOccurrenceKey, *, role: str | None) -> OccurrenceStyleIntent:
    return OccurrenceStyleIntent(key, role, None, ("table-style",),
                                 ("table-style",) if role is not None else (), ())


def _presentation_with_large_text_role():
    parts = sr.bundle()
    body = parts["theme"]["body"]
    role = "authored-table-emphasis"
    binding = dict(body["roles"]["text"])
    binding.pop("iconScale", None)
    binding.pop("iconGap", None)
    font_token = "authored-table-emphasis-size"
    body["values"][font_token] = {"type": "number", "value": 28}
    binding["fontSize"] = font_token
    binding["contrastTreatment"] = "required"
    body["roles"][role] = binding
    body["colorBindings"][f"{role}.fill"] = "text"
    return parts, role


def test_plan_measures_and_places_table_cell_with_same_selected_role(tmp_path, monkeypatch):
    captured = {}
    original = planner.prepare_surface_render_plan
    presentation, selected_role = _presentation_with_large_text_role()

    def prepare(value):
        cell = next(item for item in value.table.cells if item.style_key is not None)
        key = cell.style_key
        baseline = original(value)
        index = OccurrenceStyleIndex((_intent(key, role=selected_role),))
        styled_input = replace(value, content=replace(value.content, style_intents=index))
        selected = original(styled_input)
        captured.update(value=styled_input, baseline=baseline, selected=selected, key=key)
        return selected

    monkeypatch.setattr(usecase, "prepare_surface_render_plan", prepare)
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=2), presentation=presentation)

    value, baseline, selected, key = (captured[name] for name in ("value", "baseline", "selected", "key"))
    measured_source_cells = selected.measured.inputs["table"].table.cells
    measured_source_cell = next(item for item in measured_source_cells if item.style_key == key)
    bounded = selected.measured.bounded_tables["table"]
    bounded_cell = next(item for item in bounded.cells if item.source_ref == key.subject_id
                        and item.column_id == key.column_id)
    baseline_bounded = baseline.measured.bounded_tables["table"]
    baseline_cell = next(item for item in baseline_bounded.cells if item.source_ref == key.subject_id
                         and item.column_id == key.column_id)
    assert measured_source_cell.typography_role == selected_role
    assert bounded_cell.typography_role == selected_role
    assert bounded_cell.block_size > baseline_cell.block_size
    row_demand = dict(bounded.row_text_blocks)[key.row_id]
    baseline_row_demand = dict(baseline_bounded.row_text_blocks)[key.row_id]
    assert row_demand > baseline_row_demand

    from chrona.presentation.layout.surface_count_closure import _compose

    completed = _compose(value, selected).placement
    placed = next(item for item in completed.text if item.placement_id == f"cell:{key.subject_id}:{key.column_id}")
    assert placed.typography_role == selected_role
    assert placed.theme_role == selected_role
    assert placed.style_occurrence_key == key
    assert placed.semantic_id == next(item.semantic_id for item in selected.content.table_cells
                                       if item.style_key == key)
    primitive = next(item for item in rendered.surface.primitives
                     if item.scene_id == placed.placement_id)
    binding = semantic_binding(placed.semantic_id)
    assert primitive.semantic_id == placed.semantic_id
    assert primitive.theme_role == selected_role
    assert primitive.visual_role == binding.scene_role
    assert primitive.purpose == binding.purpose
    assert primitive.text_layout.font_size == 28
    assert primitive.paint.fill == ThemeTokenView(value.theme).color(selected_role)

    baseline_value = replace(value, content=replace(value.content, style_intents=OccurrenceStyleIndex()))
    unstyled = _compose(baseline_value, baseline).placement
    old = next(item for item in unstyled.text if item.placement_id == placed.placement_id)
    assert old.theme_role is None
    assert old.style_occurrence_key is None


def test_unstyled_table_resolution_preserves_content_and_table_identity():
    cell = TableCellContent("item", "title", "A", "tableCell", style_key=None)
    index = OccurrenceStyleIndex()
    content = type("Content", (), {"style_intents": index, "table_cells": (cell,)})()
    table = type("Table", (), {"cells": (cell,)})()
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"roles": {}, "values": {}},
    })
    resolved_content, resolved_table = resolve_table_cell_typography(content, table, tokens)
    assert resolved_content is content
    assert resolved_table is table


def test_selected_role_without_complete_text_treatment_is_incompatible():
    key = StyleOccurrenceKey("item", "primary", "tableCell", "row", "member", "title", "table-cell")
    cell = TableCellContent("item", "title", "A", "tableCell", style_key=key)
    index = OccurrenceStyleIndex((_intent(key, role="missing-font-role"),))
    content = type("Content", (), {"style_intents": index, "table_cells": (cell,)})()
    table = type("Table", (), {"cells": (cell,)})()
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"roles": {}, "values": {}},
    })
    with pytest.raises(LayoutError, match="E_STYLE_ROLE_INCOMPATIBLE") as caught:
        resolve_table_cell_typography(content, table, tokens)
    assert caught.value.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert caught.value.path == "/body/roles/missing-font-role/fontFamily"
    assert caught.value.node_id == "item"
    assert "ruleIds=table-style" in caught.value.detail
    assert "table-cell" in caught.value.detail


def test_selected_role_without_scene_text_fill_is_incompatible():
    key = StyleOccurrenceKey("item", "primary", "tableCell", "row", "member", "title", "table-cell")
    cell = TableCellContent("item", "title", "A", "tableCell", style_key=key)
    index = OccurrenceStyleIndex((_intent(key, role="text-no-fill"),))
    content = type("Content", (), {"style_intents": index, "table_cells": (cell,)})()
    table = type("Table", (), {"cells": (cell,)})()
    values = {
        "family": {"type": "fontFamily", "value": "sans"},
        "weight": {"type": "fontWeight", "value": 400},
        "size": {"type": "number", "value": 14},
        "line": {"type": "number", "value": 1.4},
        "spacing": {"type": "number", "value": 0},
        "transform": {"type": "textTransform", "value": "none"},
        "numeric": {"type": "numericSpacing", "value": "proportional"},
    }
    roles = {"text-no-fill": {
        "fontFamily": "family", "fontWeight": "weight", "fontSize": "size",
        "lineHeight": "line", "letterSpacing": "spacing", "textTransform": "transform",
        "numericSpacing": "numeric",
    }}
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"roles": roles, "values": values},
    })
    with pytest.raises(LayoutError, match="E_STYLE_ROLE_INCOMPATIBLE") as caught:
        resolve_table_cell_typography(content, table, tokens)
    assert caught.value.path == "/body/roles/text-no-fill/fill"


def test_selected_state_text_role_requires_contrast_treatment():
    semantic = next(item for item in semantic_ids()
                    if semantic_binding(item).contrast_class is ContrastClass.STATE_TEXT)
    key = StyleOccurrenceKey("item", "primary", semantic, "row", "member", "title", "table-cell")
    cell = TableCellContent("item", "title", "A", semantic, style_key=key)
    index = OccurrenceStyleIndex((_intent(key, role="text-without-contrast"),))
    content = type("Content", (), {"style_intents": index, "table_cells": (cell,)})()
    table = type("Table", (), {"cells": (cell,)})()
    values = {
        "family": {"type": "fontFamily", "value": "sans"},
        "weight": {"type": "fontWeight", "value": 400},
        "size": {"type": "number", "value": 14},
        "line": {"type": "number", "value": 1.4},
        "spacing": {"type": "number", "value": 0},
        "transform": {"type": "textTransform", "value": "none"},
        "numeric": {"type": "numericSpacing", "value": "proportional"},
        "ink": {"type": "color", "value": "#111111"},
    }
    roles = {"text-without-contrast": {
        "fontFamily": "family", "fontWeight": "weight", "fontSize": "size",
        "lineHeight": "line", "letterSpacing": "spacing", "textTransform": "transform",
        "numericSpacing": "numeric", "fill": "ink",
    }}
    tokens = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"roles": roles, "values": values},
    })
    with pytest.raises(LayoutError, match="E_STYLE_ROLE_INCOMPATIBLE") as caught:
        resolve_table_cell_typography(content, table, tokens)
    assert caught.value.path == "/body/roles/text-without-contrast/contrastTreatment"
