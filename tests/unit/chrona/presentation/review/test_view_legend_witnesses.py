from chrona.presentation.model.color_scale import ResolvedColorScale
from chrona.presentation.model.style_fills import StyleFillIndex
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleFieldFact, StyleOccurrence,
    StyleOccurrenceKey,
)
from chrona.presentation.model.surface_content import SummaryContent, SurfaceContentInput, SurfaceLegendEntry
from chrona.presentation.review.view_legend_witnesses import bind_view_legend_witnesses
from chrona.presentation.style import (
    StyleEncodingOutcome, StyleFieldSource, StyleLegendScope, StyleRule, StyleSelector,
)


def _content(entries, intents, scale):
    return SurfaceContentInput(
        table_columns=(), table_cells=(), relations=(), annotations=(), show_member_labels=False,
        label_placement="none", label_content=(), label_side="auto", label_overflow="visible-overflow",
        relation_overflow="visible-overflow", group_presentation="band", axis_tiers=(), axis_fiscal_start_month=1,
        as_of=None, as_of_label="As of", annotation_numbered=False, calendar_closed=(), calendar_exceptions=(),
        notes=(), legend_entries=entries, coverage_text="", summary=SummaryContent(()), template_values=(),
        group_details=(), milestones=(), observation_columns=(), observation_rows=(),
        style_intents=OccurrenceStyleIndex(intents), style_fills=StyleFillIndex(scales=(scale,)),
    )


def _occurrence(value, semantic="planned"):
    key = StyleOccurrenceKey("task-1", "primary", semantic)
    occurrence = StyleOccurrence(key, semantic, "mark", fields=(StyleFieldFact("owner", "string", True, value),))
    return key, occurrence


def _intent(key, *, view=True, scale_id="owners"):
    rule_ids = ("view-colorEncoding:planned",) if view else ("style:override",)
    return OccurrenceStyleIntent(
        key, None, StyleEncodingOutcome("fill", StyleFieldSource(field_name="owner"), scale_id,
                                        "firstAppearance"),
        rule_ids, (), rule_ids,
    )


def _scale():
    return ResolvedColorScale("owners", None, "owner", ("a", "b", "c"),
                              (("a", "#112233"), ("b", "#112233"), ("c", "#8899aa")),
                              folded=("c",), palette_size=2)


def _encoding_rule():
    return StyleRule("view-colorEncoding:planned", StyleSelector(semantic="planned"),
                     StyleEncodingOutcome("fill", StyleFieldSource(field_name="owner"),
                                          "owners", "firstAppearance"), "/body/colorEncoding")


def test_view_legend_binding_uses_occurrence_and_domain_identity_not_equal_ink():
    scale = _scale()
    first_key, first = _occurrence("a")
    second_key, second = _occurrence("b", "actual")
    content = _content((SurfaceLegendEntry("scale:owners:a", "a"),
                        SurfaceLegendEntry("scale:owners:b", "b"),
                        SurfaceLegendEntry("scale:owners#other", "Other")),
                       (_intent(first_key), _intent(second_key)), scale)

    result = bind_view_legend_witnesses(content, (first, second), (_encoding_rule(),), scale)

    assert result.legend_entries[0].style_occurrences == (first_key,)
    assert result.legend_entries[1].style_occurrences == (second_key,)
    assert result.legend_entries[2].style_occurrences == ()


def test_view_legend_binding_uses_folded_other_union_and_preserves_style_scope():
    scale = _scale()
    folded_key, folded = _occurrence("c")
    untouched = SurfaceLegendEntry(
        "authored", "Scope: a", style_scope=StyleLegendScope("style", "rule", "owners", "{}", "Scope", True),
        style_value="a",
    )
    content = _content((SurfaceLegendEntry("scale:owners#other", "Other"), untouched),
                       (_intent(folded_key),), scale)

    result = bind_view_legend_witnesses(content, (folded,), (_encoding_rule(),), scale)

    assert result.legend_entries[0].style_occurrences == (folded_key,)
    assert result.legend_entries[1] is untouched


def test_view_legend_binding_ignores_non_view_override_and_is_noop_without_scale():
    scale = _scale()
    key, occurrence = _occurrence("a")
    entry = SurfaceLegendEntry("scale:owners:a", "a")
    content = _content((entry,), (_intent(key, view=False),), scale)

    result = bind_view_legend_witnesses(content, (occurrence,), (_encoding_rule(),), scale)
    assert result.legend_entries[0].style_occurrences == ()
    assert bind_view_legend_witnesses(content, (occurrence,), (_encoding_rule(),), None) is content
