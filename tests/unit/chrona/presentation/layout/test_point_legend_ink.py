from dataclasses import replace
import pytest

from chrona.presentation.layout.legend_ink import point_key_owner, source_point_keys
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrence, StyleOccurrenceKey,
)
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


@pytest.mark.parametrize("state", ("planned", "actual", "forecast"))
@pytest.mark.parametrize("selected_role", ("planned", "actual", "forecast"))
def test_explicit_builtin_style_role_owns_points_ahead_of_general_milestone(state, selected_role):
    occurrence = _occurrence(state)
    intent = OccurrenceStyleIntent(occurrence.key, selected_role, None,
                                  ("select-role",), ("select-role",), ())
    content = _content((SurfaceLegendEntry("milestone", "Milestones"),
                        *(SurfaceLegendEntry(role, role.title())
                          for role in ("planned", "actual", "forecast"))),
                       (occurrence,), intents=OccurrenceStyleIndex((intent,)))

    keys = source_point_keys(content, _tokens(), mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities())

    assert len(keys) == 1
    assert keys[0].family == selected_role
    assert keys[0].point_state == state
    assert keys[0].paint_role == selected_role


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


def _encoded_content(*, scope="view", covered=True, visible=True):
    from chrona.presentation.model.style_fills import CompletedStyleFill, StyleFillIndex
    from chrona.presentation.style import EncodingSource, EncodingWitness

    occurrences = tuple(_occurrence("planned", subject=subject) for subject in ("a", "b"))
    source = EncodingSource("view", "view", "/body/colorEncoding") if scope == "view" else (
        EncodingSource("style", "style", "/body/rules/0", "paint"))
    fills = tuple((occurrence.key, CompletedStyleFill(color, EncodingWitness(
        "fill", "owners", "owner", subject, (source,))))
        for occurrence, color, subject in zip(occurrences, ("#112233", "#998877"), ("a", "b")))
    entries = [SurfaceLegendEntry("milestone", "Gate")]
    if covered:
        for occurrence, _ in fills:
            values = dict(style_occurrences=(occurrence,), swatch_visible=visible)
            if scope == "view":
                values.update(view_scale_id="owners", view_scale_domain_value=occurrence.subject_id)
            else:
                # Folded Other deliberately differs from the raw encoded value.
                values.update(style_scope=StyleLegendScope("style", "paint", "owners", "field", None, True),
                              style_value="Other")
            entries.append(SurfaceLegendEntry(f"scale:{occurrence.subject_id}", "Owner", **values))
    return replace(_content(entries, occurrences), style_fills=StyleFillIndex(fills))


@pytest.mark.parametrize("scope", ("view", "style"))
def test_separately_keyed_encoding_uses_one_neutral_state_key_and_retains_actual_ink(scope):
    from chrona.presentation.layout.legend_candidates import coalesce_point_keys
    content = _encoded_content(scope=scope)
    keys = source_point_keys(content, _tokens(), mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities())
    key, = coalesce_point_keys(keys)
    assert key.glyph.paints[0].effective_channels.fill == "#345678"
    assert key.occurrences == tuple(item.key for item in content.legend_mark_occurrences)
    assert {witness.paints[0].effective_channels.fill for witness in key.encoding_witnesses} == {
        "#112233", "#998877"}
    assert key.legend_encoding_coverage.kind == "state"
    assert {witness.value for witness in key.legend_encoding_coverage.witnesses} == {"a", "b"}


@pytest.mark.parametrize("case", ("absent", "hidden", "wrong-scale", "wrong-occurrence"))
def test_unexplained_encoded_paint_still_splits_state_keys(case):
    from chrona.presentation.layout.legend_candidates import coalesce_point_keys
    content = _encoded_content(covered=case != "absent", visible=case != "hidden")
    if case == "wrong-scale":
        content = replace(content, legend_entries=tuple(replace(entry, view_scale_id="other")
            if entry.view_scale_id is not None else entry for entry in content.legend_entries))
    elif case == "wrong-occurrence":
        content = replace(content, legend_entries=tuple(replace(entry, style_occurrences=())
            for entry in content.legend_entries))
    keys = coalesce_point_keys(source_point_keys(content, _tokens(), mark_block_size=20,
                              paint_capabilities=PaintWitnessCapabilities()))
    assert len(keys) == 2
    assert {key.glyph.paints[0].effective_channels.fill for key in keys} == {"#112233", "#998877"}
    assert all(key.legend_encoding_coverage is None for key in keys)


def test_neutralization_preserves_explicit_multipart_ink_and_replaces_only_encoded_parts():
    from chrona.presentation.layout.legend_ink import _keys
    from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
    content = _encoded_content()
    parts = (SymbolPartPlacement((), paint_mode="fill"),
             SymbolPartPlacement((), paint_mode="fill", paint_color="#FF0000"))
    key, = _keys(content, _tokens(), PaintWitnessCapabilities(),
        key=content.legend_mark_occurrences[0].key, selected_role=None, parts=parts,
        default_role="planned", family_id="milestone", glyph_footprint=(10, 10),
        point_state="planned", point_geometry=("two-parts",))
    assert tuple(paint.effective_channels.fill for paint in key.glyph.paints) == ("#345678", "#FF0000")
    assert tuple(paint.effective_channels.fill for paint in key.encoding_witnesses[0].paints) == ("#112233", "#FF0000")

    explicit, = _keys(content, _tokens(), PaintWitnessCapabilities(),
        key=content.legend_mark_occurrences[0].key, selected_role=None, parts=parts[1:],
        default_role="planned", family_id="milestone", glyph_footprint=(10, 10), point_state="planned")
    assert explicit.glyph.paints[0].effective_channels.fill == "#FF0000"
    assert explicit.legend_encoding_coverage is None


def test_neutral_state_representative_restores_the_declared_role_gradient():
    tokens = _tokens()
    body = dict(tokens._body)
    body["values"] = {**body["values"],
        "end": {"type": "color", "value": "#ABCDEF"},
        "angle": {"type": "number", "value": 45}}
    body["roles"] = {**body["roles"], "planned": {**body["roles"]["planned"],
        "gradientStart": "ink", "gradientEnd": "end", "gradientAngle": "angle"}}
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": body})
    keys = source_point_keys(_encoded_content(), tokens, mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities())
    assert all(key.glyph.paints[0].gradient.admitted for key in keys)
    assert all(key.encoding_witnesses[0].paints[0].gradient is None for key in keys)
    assert len({key.grouping_identity for key in keys}) == 1


def test_neutral_state_keeps_a_hollow_theme_role_without_inventing_fill():
    tokens = _tokens()
    body = dict(tokens._body)
    body["values"] = {**body["values"],
        "outline": {"type": "pattern", "value": {"kind": "outline"}},
        "width": {"type": "number", "value": 1}}
    body["roles"] = {**body["roles"], "planned": {**body["roles"]["planned"],
        "pattern": "outline", "stroke": "ink", "strokeWidth": "width"}}
    body["roles"]["planned"].pop("fill")
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": body})
    keys = source_point_keys(_encoded_content(), tokens, mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities())
    assert all(key.glyph.paints[0].effective_channels.fill is None for key in keys)
    assert all(key.glyph.paints[0].effective_channels.stroke == "#345678" for key in keys)
    assert all(key.legend_encoding_coverage.kind == "state" for key in keys)


def test_same_scale_and_occurrence_do_not_waive_mismatched_encoding_origin():
    from chrona.presentation.layout.legend_candidates import coalesce_point_keys
    content = _encoded_content(scope="style")
    content = replace(content, legend_entries=tuple(replace(entry,
        style_scope=replace(entry.style_scope, rule_id="unrelated"))
        if entry.style_scope is not None else entry for entry in content.legend_entries))
    keys = coalesce_point_keys(source_point_keys(content, _tokens(), mark_block_size=20,
                              paint_capabilities=PaintWitnessCapabilities()))
    assert len(keys) == 2
    assert all(key.legend_encoding_coverage is None for key in keys)


def test_explicit_rule_pair_encoding_key_still_explains_its_source_colour():
    from chrona.presentation.layout.legend_candidates import coalesce_point_keys
    content = _encoded_content()
    content = replace(content, legend_entries=tuple(replace(entry, swatch_shape="rule-pair")
        if entry.encoding_scale_id is not None else entry for entry in content.legend_entries))
    key, = coalesce_point_keys(source_point_keys(content, _tokens(), mark_block_size=20,
                             paint_capabilities=PaintWitnessCapabilities()))
    assert key.glyph.paints[0].effective_channels.fill == "#345678"
    assert {witness.value for witness in key.legend_encoding_coverage.witnesses} == {"a", "b"}
