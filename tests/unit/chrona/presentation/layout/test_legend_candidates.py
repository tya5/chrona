from __future__ import annotations

from chrona.presentation.layout import legend_candidates
from chrona.presentation.layout.legend_candidates import prepare_realized_legend_candidates
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.style_rules import StyleOccurrence, StyleOccurrenceKey
from chrona.presentation.model.surface_content import SummaryContent, SurfaceContentInput, SurfaceLegendEntry
from chrona.presentation.model.theme_paint import PaintFamily, resolve_theme_paint_witness
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.layout.legend_ink import source_actual_keys


def _content(entries, **overrides):
    values = dict(
        table_columns=(), table_cells=(), relations=(), annotations=(), show_member_labels=False,
        label_placement="none", label_content=(), label_side="auto", label_overflow="visible-overflow",
        relation_overflow="visible-overflow", group_presentation="band", axis_tiers=(), axis_fiscal_start_month=1,
        as_of=None, as_of_label="As of", annotation_numbered=False,
        calendar_closed=(), calendar_exceptions=(), notes=(), legend_entries=tuple(entries), coverage_text="",
        summary=SummaryContent(()), template_values=(), group_details=(), milestones=(),
        observation_columns=(), observation_rows=(),
    )
    values.update(overrides)
    return SurfaceContentInput(**values)


def _tokens():
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"base": {"type": "color", "value": "#123456"}},
                 "roles": {"actual": {"fill": "base"}, "progress-fill": {"fill": "base"}},
                 "metrics": {}},
    })


def _key(tokens, color, classes=(), occurrence_id="x", family="actual"):
    witness = resolve_theme_paint_witness(tokens, "actual", PaintFamily.SOLID, fill_override=color)
    occurrence = StyleOccurrenceKey(occurrence_id, "primary", "actual")
    return RealizedLegendKey(family, "actual", witness, (occurrence,), tuple(classes))


def test_actual_qualifier_uses_actual_trait_not_forecast_display_delta():
    source = StyleOccurrence(StyleOccurrenceKey("a", "combined", "actual"), "actual", "mark",
        original_roles=("actual", "variance-ahead"), comparison_category="behind", mark_shape="span")
    content = _content((SurfaceLegendEntry("actual", "Observed"),), legend_mark_occurrences=(source,))
    keys = source_actual_keys(content, _tokens(), mark_block_size=10,
                              paint_capabilities=PaintWitnessCapabilities())
    assert len(keys) == 1 and keys[0].variance_classes == ("ahead",)


def test_actual_candidates_coalesce_equal_paint_and_label_all_realized_classes(monkeypatch):
    tokens = _tokens()
    keys = (
        _key(tokens, "#111111", ("ahead",), "a"),
        _key(tokens, "#111111", ("behind",), "b"),
        _key(tokens, "#222222", ("behind",), "c"),
        _key(tokens, "#333333", ("behind",), "d"),
    )
    monkeypatch.setattr(legend_candidates, "source_actual_keys", lambda *args, **kwargs: keys)
    content = _content((SurfaceLegendEntry("actual", "Observed"), SurfaceLegendEntry("planned", "Plan")),
                       legend_wording=(("actual", "Realized"), ("actual-behind", "Late")))

    result = prepare_realized_legend_candidates(
        content, tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())

    actual = tuple(entry for entry in result.legend_entries if entry.role == "actual")
    assert [entry.label for entry in actual] == ["Realized — Ahead / Late", "Realized — Late", "Realized — Late"]
    assert [entry.realized_key.occurrences for entry in actual] == [
        (keys[0].occurrences[0], keys[1].occurrences[0]),
        (keys[2].occurrences[0],), (keys[3].occurrences[0],),
    ]
    assert actual[1].source_identity != actual[2].source_identity
    assert [entry.role for entry in result.legend_entries] == ["actual", "actual", "actual", "planned"]


def test_progress_candidate_uses_realized_witness_preserves_explicit_position_and_drops_when_absent(monkeypatch):
    tokens = _tokens()
    monkeypatch.setattr(legend_candidates, "source_actual_keys", lambda *args, **kwargs: ())
    explicit = SurfaceLegendEntry("progressFill", "Percent complete", swatch_shape="circle")
    content = _content((SurfaceLegendEntry("planned", "Plan"), explicit,
                        SurfaceLegendEntry("actual", "Actual"), SurfaceLegendEntry("scale:owner", "Owner")),
                       legend_progress_possible=True,
                       legend_wording=(("progressFill", "Progress ink"),))

    result = prepare_realized_legend_candidates(
        content, tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())
    progress, = (entry for entry in result.legend_entries if entry.role == "progressFill")
    assert [entry.role for entry in result.legend_entries] == ["planned", "progressFill", "scale:owner"]
    assert (progress.label, progress.swatch_shape, progress.realized_key.family) == (
        "Progress ink", "circle", "progressFill")
    assert progress.realized_key.paint_role == "progress-fill"
    assert progress.realized_key.paint.identity[0] == ("solid", "#123456")
    actual = _key(tokens, "#123456")
    assert progress.realized_key.identity != actual.identity  # equal ink, distinct semantic families

    absent = prepare_realized_legend_candidates(
        _content((explicit, SurfaceLegendEntry("planned", "Plan")), legend_progress_possible=False),
        tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())
    assert [entry.role for entry in absent.legend_entries] == ["planned"]


def test_generated_progress_follows_actual_groups_then_falls_back_after_forecast(monkeypatch):
    tokens = _tokens()
    keys = (_key(tokens, "#111111", ("behind",)), _key(tokens, "#222222", ("ahead",), "y"))
    monkeypatch.setattr(legend_candidates, "source_actual_keys", lambda *args, **kwargs: keys)
    actual_content = _content((SurfaceLegendEntry("planned", "Plan"), SurfaceLegendEntry("actual", "Actual")),
                              legend_progress_possible=True)
    actual_result = prepare_realized_legend_candidates(
        actual_content, tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())
    assert [entry.role for entry in actual_result.legend_entries] == [
        "planned", "actual", "actual", "progressFill"]

    fallback = _content((SurfaceLegendEntry("forecast", "Forecast"), SurfaceLegendEntry("scale:owner", "Owner")),
                        legend_progress_possible=True)
    monkeypatch.setattr(legend_candidates, "source_actual_keys", lambda *args, **kwargs: ())
    fallback_result = prepare_realized_legend_candidates(
        fallback, tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())
    assert [entry.role for entry in fallback_result.legend_entries] == ["forecast", "progressFill", "scale:owner"]


def test_actual_candidates_consume_closed_occurrence_and_completed_trait_paint_facts():
    tokens = _tokens()
    ahead_key = StyleOccurrenceKey("a", "primary", "actual")
    behind_key = StyleOccurrenceKey("b", "primary", "actual")
    content = _content((SurfaceLegendEntry("actual", "Actual"),),
                       legend_mark_occurrences=(
                           StyleOccurrence(ahead_key, "actual", "mark", original_roles=("actual", "variance-ahead"), comparison_category="ahead", mark_shape="span"),
                           StyleOccurrence(behind_key, "actual", "mark", original_roles=("actual", "variance-behind"), comparison_category="behind", mark_shape="span"),
                       ), actual_variance_paints=(("a", "#00AA00"), ("b", "#AA0000")))

    result = prepare_realized_legend_candidates(
        content, tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())

    assert [(entry.label, entry.realized_key.paint.effective_channels.fill) for entry in result.legend_entries] == [
        ("Actual — Ahead", "#00AA00"), ("Actual — Behind", "#AA0000")]
