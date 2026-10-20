from dataclasses import replace

from chrona.presentation.layout.legend_ink import point_key_owner, source_point_keys
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.style_rules import StyleOccurrence, StyleOccurrenceKey
from chrona.presentation.model.surface_content import (
    SurfaceContentInput, SurfaceLegendEntry, SummaryContent,
)
from chrona.presentation.style import StyleLegendScope
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _tokens(*, gate=False):
    values = {
        "height": {"type": "number", "value": "0.2"},
        "order": {"type": "number", "value": 10},
        "radius": {"type": "number", "value": 0},
        "ink": {"type": "color", "value": "#345678"},
    }
    roles = {}
    for role, shape in (("planned", "square"), ("actual", "circle"),
                        ("snapshot", "circle"), ("scenario", "circle"),
                        ("missing-actual", "circle"), ("forecast", "diamond"),
                        ("milestoneSymbol", "diamond"), ("milestoneSymbolActual", "circle")):
        symbol = f"{role}-symbol"
        values[symbol] = {"type": "symbol", "value": {"shape": shape}}
        roles[role] = {"markHeight": "height", "markPaintOrder": "order",
                       "markCornerRadius": "radius", "symbol": symbol}
    roles["actual"]["fill"] = "ink"
    roles["planned"]["fill"] = "ink"
    if gate:
        roles["gate"] = {"fill": "ink"}
    roles["forecast"] = dict(roles["planned"])
    roles["forecast"]["symbol"] = "forecast-symbol"
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": values, "roles": roles}})


def _content(entries, occurrences, *, intents=()):
    values = dict(
        table_columns=(), table_cells=(), relations=(), annotations=(), show_member_labels=False,
        label_placement="none", label_content=(), label_side="auto", label_overflow="visible-overflow",
        relation_overflow="visible-overflow", group_presentation="band", axis_tiers=(),
        axis_fiscal_start_month=1, as_of=None, as_of_label="As of", annotation_numbered=False,
        calendar_closed=(), calendar_exceptions=(), notes=(), legend_entries=tuple(entries),
        coverage_text="", summary=SummaryContent(()), template_values=(), group_details=(),
        milestones=(), observation_columns=(), observation_rows=(),
        legend_mark_occurrences=tuple(occurrences),
    )
    if intents:
        values["style_intents"] = intents
    return SurfaceContentInput(**values)


def _occurrence(state, shape="point", *, subject="task", source_kind="primary"):
    key = StyleOccurrenceKey(subject, source_kind, state)
    return StyleOccurrence(key, state, "mark", mark_shape=shape)


def test_point_owner_prefers_first_eligible_selected_role_then_milestone_then_state():
    selected = "custom-point"
    entries = (
        SurfaceLegendEntry(selected, "Period", source_ref="period:week"),
        SurfaceLegendEntry(selected, "Encoding", view_scale_id="scale", view_scale_domain_value="x"),
        SurfaceLegendEntry(selected, "Style", style_scope=StyleLegendScope(
            "style", "rule", "scale", "field", "Selected", True), style_value="x"),
        SurfaceLegendEntry("milestone", "Milestones"),
        SurfaceLegendEntry("actual", "Observed"),
        SurfaceLegendEntry(selected, "First"),
        SurfaceLegendEntry(selected, "Second"),
    )
    content = _content(entries, ())

    assert point_key_owner(content, "actual", selected) == selected
    assert point_key_owner(content, "planned", None) == "milestone"
    assert point_key_owner(_content((entries[0], entries[1], entries[2], entries[4]), ()),
                           "planned", None) is None


def test_source_point_keys_preserve_state_and_completed_glyph_structure():
    occurrence = _occurrence("actual")
    entries = (SurfaceLegendEntry("actual", "Observed"),)
    content = _content(entries, (occurrence,))

    keys = source_point_keys(content, _tokens(), mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities())

    assert len(keys) == 1
    assert keys[0].family == "actual"
    assert keys[0].point_state == "actual"
    assert keys[0].glyph is not None
    assert keys[0].glyph.geometry_identity[0] == "circle"
    assert keys[0].occurrences == (occurrence.key,)


def test_point_state_partitions_equal_ink_without_changing_nonpoint_identity():
    tokens = _tokens()
    from chrona.presentation.layout.legend_candidates import source_actual_keys
    from chrona.presentation.model.theme_paint import PaintFamily, resolve_theme_paint_witness
    from chrona.presentation.model.legend_paint import RealizedLegendKey

    actual = _occurrence("actual")
    planned = _occurrence("planned")
    content = _content((SurfaceLegendEntry("planned", "Plan"),
                        SurfaceLegendEntry("actual", "Observed")), (actual, planned))
    point_keys = source_point_keys(content, tokens, mark_block_size=20,
                                   paint_capabilities=PaintWitnessCapabilities())
    assert {key.point_state for key in point_keys} == {"planned", "actual"}
    assert len({key.grouping_identity for key in point_keys}) == 2

    witness = resolve_theme_paint_witness(tokens, "actual", PaintFamily.SOLID)
    span = RealizedLegendKey("actual", "actual", witness)
    assert replace(span, point_state=None).identity == span.identity
    assert source_actual_keys(content, tokens, mark_block_size=20,
                              paint_capabilities=PaintWitnessCapabilities()) == ()


def test_gate_canonical_source_occurrence_is_reserved_as_planned_state():
    occurrence = _occurrence("gate")
    content = _content((SurfaceLegendEntry("planned", "Plan"),), (occurrence,))

    keys = source_point_keys(content, _tokens(gate=True), mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities())

    assert len(keys) == 1
    assert keys[0].point_state == "planned"
    assert keys[0].occurrences == (occurrence.key,)
    assert keys[0].paint_role == "gate"
