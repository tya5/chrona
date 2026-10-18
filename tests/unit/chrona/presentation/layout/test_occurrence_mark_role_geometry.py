from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.mark_role_geometry import (
    resolve_mark_band, resolve_mark_geometries, resolve_occurrence_mark_frame,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.model.projection import ObservationState
from chrona.presentation.model.style_rules import OccurrenceStyleIntent, StyleOccurrenceKey
from chrona.presentation.model.theme_tokens import ThemeTokenView


DAY = date(2026, 4, 12)


def _theme(*, custom_geometry=True, custom_symbol=True, actual_offset="0.1",
           gate_declared=False, stack=False):
    values = {}
    roles = {}

    def add_role(role, height, offset=None, symbol_height=None, symbol_offset=None,
                 symbol="diamond"):
        binding = {}
        for prop, value in (("markHeight", height), ("markOffset", offset),
                            ("markPaintOrder", 10), ("markCornerRadius", 0),
                            ("symbolHeight", symbol_height), ("symbolOffset", symbol_offset)):
            if value is None:
                continue
            token_id = f"{role}-{prop}"
            values[token_id] = {"type": "number", "value": value}
            binding[prop] = token_id
        if symbol is not None:
            token_id = f"{role}-symbol"
            values[token_id] = {"type": "symbol", "value": {"shape": symbol}}
            binding["symbol"] = token_id
        roles[role] = binding

    for role in ("planned", "actual", "snapshot", "scenario", "missing-actual"):
        add_role(role, "0.2" if role != "actual" else "0.1",
                 ("0.1" if not stack else None) if role == "actual" else None)
    # Existing point behavior resolves through milestoneSymbol, not the geometry role's optional symbol.
    add_role("milestoneSymbol", "0.2", symbol="diamond")
    if custom_geometry:
        add_role("custom-plan", "0.4", None if stack else "0.2", "0.5", "0.25",
                 symbol="square" if custom_symbol else None)
        add_role("custom-actual", "0.2", None if stack else actual_offset, symbol_height=None,
                 symbol_offset=None, symbol=None)
    if gate_declared:
        add_role("gate", "0.3", "0.2", "0.4", "0.3", symbol="square")
    if stack:
        values["stack-gap"] = {"type": "number", "value": "0.04"}
    body = {"values": values, "roles": roles}
    if stack:
        body["markStack"] = {"members": [["planned"], ["actual"]], "gap": "stack-gap"}
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                          "body": body})


def _frame(theme):
    scale = ScalePlacement("surface", "test", date(2026, 1, 1), date(2026, 5, 1), 0, 100, 0, 1)
    geometries = resolve_mark_geometries(theme)
    allocation = resolve_mark_band(theme, 100, role_geometries=geometries)
    return MarkBandFrame.zero_origin(scale, 100, geometries, allocation)


def _item(*, source_type="point", actual=None, state=ObservationState.UNAVAILABLE,
          forecast=None, planned=None):
    planned = planned or ({"at": DAY} if source_type == "point" else
                          {"start": DAY, "end": date(2026, 4, 20)})
    return SimpleNamespace(object_id="task-17", title="Task 17", source_type=source_type,
                           planned=planned, actual=actual or {}, observation_state=state,
                           missing_actual_mark="due-end", forecast=forecast)


def _intent(semantic, role, *, source_kind="primary", rule_ids=("role-rule",)):
    key = StyleOccurrenceKey("task-17", source_kind, semantic)
    return OccurrenceStyleIntent(key, role, None, rule_ids, rule_ids, ())


def test_unstyled_point_behavior_and_geometry_frame_remain_unchanged():
    theme = _theme()
    frame = _frame(theme)
    assert resolve_occurrence_mark_frame(frame, theme, None) is frame

    result = compose_item_marks(item=_item(), instance_id="row-17", source_kind="primary",
                                frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline")
    mark = result.marks[0]
    assert mark.theme_role is None and mark.style_occurrence_key is None
    # Existing unstyled variant fallback is the Theme's milestoneSymbol diamond.
    assert mark.symbol_parts[0].commands[0].points[0] == (
        float(mark.bounds.inline + mark.bounds.inline_size / 2), float(mark.bounds.block))


def test_selected_role_geometry_symbol_and_identity_are_completed_before_placement():
    theme = _theme()
    frame = _frame(theme)
    intent = _intent("planned", "custom-plan")
    result = compose_item_marks(item=_item(), instance_id="row-17", source_kind="primary",
                                frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline",
                                style_intents={"planned": intent})
    mark = result.marks[0]

    assert mark.theme_role == "custom-plan"
    assert mark.style_occurrence_key == intent.key
    assert (float(mark.bounds.block), float(mark.bounds.block_size)) == (25, 50)
    # The exact selected role's square symbol starts at the top-left, unlike the old diamond fallback.
    assert mark.symbol_parts[0].commands[0].points[0] == (
        float(mark.bounds.inline), float(mark.bounds.block))


def test_actual_symbol_fallback_uses_the_selected_planned_frame():
    theme = _theme()
    frame = _frame(theme)
    intents = {"planned": _intent("planned", "custom-plan", source_kind="combined"),
               "actual": _intent("actual", "custom-actual", source_kind="combined")}
    selected = resolve_occurrence_mark_frame(frame, theme, intents)
    block, size = selected.symbol_bounds("actual")
    assert (block, size) == (25, 50)


def test_selected_role_without_mark_geometry_fails_with_style_context():
    theme = _theme(custom_geometry=False)
    intent = _intent("planned", "missing-role")
    with pytest.raises(LayoutError) as raised:
        compose_item_marks(item=_item(), instance_id="row-17", source_kind="primary",
                           frame=_frame(theme), as_of=None, theme_tokens=theme, slot_id="timeline",
                           style_intents={"planned": intent})
    error = raised.value
    assert error.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert "role-rule" in error.detail and "StyleOccurrenceKey" in error.detail
    assert "task-17" in error.detail and "missing-role" in error.detail


def test_selected_point_role_without_its_own_symbol_fails_without_fallback():
    theme = _theme(custom_symbol=False)
    intent = _intent("planned", "custom-plan")
    with pytest.raises(LayoutError) as raised:
        compose_item_marks(item=_item(), instance_id="row-17", source_kind="primary",
                           frame=_frame(theme), as_of=None, theme_tokens=theme, slot_id="timeline",
                           style_intents={"planned": intent})
    error = raised.value
    assert error.diagnostic_id == "E_STYLE_ROLE_INCOMPATIBLE"
    assert error.path == "/body/roles/custom-plan/symbol"
    assert "role-rule" in error.detail and "task-17" in error.detail


def test_gate_style_identity_joins_only_the_existing_primary_point_binding():
    theme = _theme(gate_declared=True)
    frame = _frame(theme)
    gate_intent = _intent("gate", "custom-plan", rule_ids=("gate-rule",))

    point = compose_item_marks(item=_item(), instance_id="row-17", source_kind="primary",
                               frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline",
                               style_intents={"gate": gate_intent}).marks[0]
    assert point.semantic_id == "planned"  # logical identity and placement remain stable
    assert point.theme_role == "custom-plan"
    assert point.style_occurrence_key == gate_intent.key
    assert point.style_occurrence_key.semantic_id == "gate"

    span = compose_item_marks(item=_item(source_type="span"), instance_id="row-17", source_kind="primary",
                              frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline",
                              style_intents={"gate": gate_intent}).marks[0]
    assert span.semantic_id == "planned" and span.theme_role is None
    assert span.style_occurrence_key is None

    forecast = SimpleNamespace(schedule=SimpleNamespace(placement={"at": DAY}))
    forecast_item = _item(forecast=forecast)
    retained_forecast = _intent("forecast", "custom-plan", rule_ids=("forecast-rule",))
    forecast_mark = compose_item_marks(
        item=forecast_item, instance_id="row-17", source_kind="primary", frame=frame,
        as_of=None, theme_tokens=theme, slot_id="timeline",
        style_intents={"gate": gate_intent, "forecast": retained_forecast}).marks[0]
    assert forecast_mark.semantic_id == "forecast"
    assert forecast_mark.theme_role == "custom-plan"
    assert forecast_mark.style_occurrence_key == retained_forecast.key


def test_unselected_actual_point_uses_the_occurrence_frame_actual_symbol_fallback():
    theme = _theme()
    frame = _frame(theme)
    planned_intent = _intent("planned", "custom-plan", source_kind="combined")
    item = _item(actual={"at": date(2026, 4, 14)}, state=ObservationState.RECORDED)

    result = compose_item_marks(
        item=item, instance_id="row-17", source_kind="combined", frame=frame,
        as_of=None, theme_tokens=theme, slot_id="timeline",
        style_intents={"planned": planned_intent})
    styled_frame = resolve_occurrence_mark_frame(frame, theme, {"planned": planned_intent})
    planned, actual = result.marks

    assert (float(planned.bounds.block), float(planned.bounds.block_size)) == styled_frame.symbol_bounds("planned")
    assert (float(actual.bounds.block), float(actual.bounds.block_size)) == styled_frame.symbol_bounds("actual")
    assert planned.theme_role == "custom-plan" and planned.style_occurrence_key == planned_intent.key
    assert actual.theme_role is None and actual.style_occurrence_key is None


def test_unselected_actual_span_uses_the_occurrence_frames_recomputed_stack():
    theme = _theme(stack=True)
    frame = _frame(theme)
    planned_intent = _intent("planned", "custom-plan", source_kind="combined")
    item = _item(source_type="span", actual={"start": date(2026, 4, 13),
                                               "finish": date(2026, 4, 18)},
                 state=ObservationState.RECORDED)

    result = compose_item_marks(
        item=item, instance_id="row-17", source_kind="combined", frame=frame,
        as_of=None, theme_tokens=theme, slot_id="timeline",
        style_intents={"planned": planned_intent})
    styled_frame = resolve_occurrence_mark_frame(frame, theme, {"planned": planned_intent})
    planned, actual = result.marks

    assert (float(planned.bounds.block), float(planned.bounds.block_size)) == styled_frame.role_bounds("planned")
    assert (float(actual.bounds.block), float(actual.bounds.block_size)) == styled_frame.role_bounds("actual")
    assert float(actual.bounds.block) != frame.role_bounds("actual")[0]
    assert planned.theme_role == "custom-plan" and planned.style_occurrence_key == planned_intent.key
    assert actual.theme_role is None and actual.style_occurrence_key is None
