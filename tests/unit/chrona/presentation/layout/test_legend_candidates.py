from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout import legend_candidates
from chrona.presentation.layout.legend_candidates import prepare_realized_legend_candidates
from chrona.presentation.model.legend_paint import RealizedGlyphInk, RealizedLegendKey
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


def test_composite_identity_keeps_geometry_and_order_but_not_role_names_or_footprints():
    first = _key(_tokens(), "#123456", ("ahead",), "a")
    inner = _key(_tokens(), "#111111").paint
    glyph = RealizedGlyphInk(None, (("outer",), ("inner",)),
                             (first.paint, inner), (12.0, 14.0))
    first = replace(first, glyph=glyph)
    second = replace(_key(_tokens(), "#123456", ("behind",), "b"),
                     glyph=replace(glyph, selected_role="alias", footprint=(16.0, 10.0)))

    assert first.identity == second.identity
    assert first.identity != replace(first, glyph=None).identity
    assert first.identity != replace(first, glyph=replace(glyph, paints=glyph.paints[::-1])).identity
    assert first.identity != replace(first, glyph=replace(glyph, geometry_identity=(("other",),))).identity
    grouped, = legend_candidates.coalesce_actual_keys((first, second))
    assert grouped.glyph.footprint == (16.0, 14.0)
    assert grouped.occurrences == (*first.occurrences, *second.occurrences)
    assert grouped.variance_classes == ("ahead", "behind")


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
    assert [entry.label for entry in actual] == ["Realized", "Late", "Late"]
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
        ("Ahead", "#00AA00"), ("Behind", "#AA0000")]


def test_actual_grouping_ignores_fill_stroke_and_outline_geometry_but_keeps_ink_and_family():
    tokens = _tokens()
    fill = _key(tokens, "#123456", ("ahead",), "fill")
    stroke_paint = replace(fill.paint, effective_channels=replace(
        fill.paint.effective_channels, fill=None, stroke="#123456", stroke_width=2))
    stroke = replace(fill, paint=stroke_paint, occurrences=(StyleOccurrenceKey("stroke", "primary", "actual"),),
                     variance_classes=("behind",))
    different = _key(tokens, "#654321", ("behind",), "different")

    grouped = legend_candidates.coalesce_actual_keys((fill, stroke, different))

    assert len(grouped) == 2
    assert grouped[0].occurrences == (*fill.occurrences, *stroke.occurrences)
    assert grouped[0].variance_classes == ("ahead", "behind")
    assert grouped[0].identity == fill.identity  # representative retains its exact paint witness
    assert stroke.identity != fill.identity
    assert grouped[0].grouping_identity == fill.grouping_identity
    assert _key(tokens, "#123456", family="progressFill").grouping_identity != fill.grouping_identity


def test_fill_palette_ignores_decorative_border_for_grouping_and_progress_suppression(monkeypatch):
    from types import SimpleNamespace

    from chrona.presentation.layout import realized_legend

    tokens = _tokens()
    fill = _key(tokens, "#123456")
    outlined = replace(fill, paint=replace(fill.paint, effective_channels=replace(
        fill.paint.effective_channels, stroke="#FFF8E8", stroke_width=Decimal(1))))
    progress = _key(tokens, "#123456", family="progressFill")
    assert outlined.identity != fill.identity
    assert outlined.grouping_identity == fill.grouping_identity

    host = SimpleNamespace(placement_id="host", semantic_id="actual", mark_shape="span")
    shape = SimpleNamespace(host_placement_id="host")
    monkeypatch.setattr(realized_legend, "actual_mark_keys", lambda *args: (outlined,))
    assert not realized_legend._progress_adds_actual_ink(progress, (shape,), (host,), _content(()), tokens,
                                                         PaintWitnessCapabilities())


def test_point_states_expand_at_owner_position_without_overriding_authored_labels(monkeypatch):
    tokens = _tokens()
    keys = tuple(replace(_key(tokens, "#123456", occurrence_id=state, family="milestone"),
                         point_state=state) for state in ("forecast", "planned", "actual"))
    monkeypatch.setattr(legend_candidates, "source_point_keys", lambda *args, **kwargs: keys)
    content = _content((SurfaceLegendEntry("planned", "Timeline"),
                        SurfaceLegendEntry("milestone", "Review"), SurfaceLegendEntry("background", "Canvas")),
                       legend_defaults=(("planned-plain", "Plan"), ("actual", "Actual"),
                                        ("forecast", "Estimate"), ("milestone", "Milestone")))
    result = prepare_realized_legend_candidates(content, tokens, mark_block_size=10,
                                               paint_capabilities=PaintWitnessCapabilities())
    assert [entry.label for entry in result.legend_entries] == [
        "Timeline", "Review · Plan", "Review · Actual", "Review · Estimate", "Canvas"]
    assert len({entry.source_identity for entry in result.legend_entries[1:4]}) == 3


def test_point_owner_single_state_keeps_label_and_actual_span_stays_separate(monkeypatch):
    tokens = _tokens()
    span = _key(tokens, "#123456")
    point = replace(span, point_state="actual")
    monkeypatch.setattr(legend_candidates, "source_actual_keys", lambda *args, **kwargs: (span,))
    monkeypatch.setattr(legend_candidates, "source_point_keys", lambda *args, **kwargs: (point,))
    content = _content((SurfaceLegendEntry("actual", "Observed"),),
                       legend_defaults=(("actual", "Actual"), ("milestone", "Gate")))
    result = prepare_realized_legend_candidates(content, tokens, mark_block_size=10,
                                               paint_capabilities=PaintWitnessCapabilities())
    assert [entry.label for entry in result.legend_entries] == ["Observed", "Observed · Gate"]
    assert result.legend_entries[0].source_identity != result.legend_entries[1].source_identity

    monkeypatch.setattr(legend_candidates, "source_point_keys", lambda *args, **kwargs: (
        replace(point, family="review"),))
    result = prepare_realized_legend_candidates(_content((SurfaceLegendEntry("review", "Decision"),)),
        tokens, mark_block_size=10, paint_capabilities=PaintWitnessCapabilities())
    assert [entry.label for entry in result.legend_entries] == ["Decision"]


def test_multipart_fill_palette_uses_all_fill_parts_not_outline_inks():
    tokens = _tokens()
    first = _key(tokens, "#123456")
    red_part = replace(first.paint, effective_channels=replace(
        first.paint.effective_channels, stroke="#FFF8E8", stroke_width=Decimal(1)))
    blue_part = replace(first.paint, effective_channels=replace(
        first.paint.effective_channels, fill="#654321", stroke="#ABCDEF", stroke_width=Decimal(1)))
    glyph = RealizedGlyphInk(None, (("first",), ("second",)), (red_part, blue_part), (12, 12))
    key = replace(first, glyph=glyph)

    assert key.ink_identity == (
        ((("color", "#123456"), Decimal(1)), (("color", "#654321"), Decimal(1))), None)


def test_actual_grouping_coalesces_glyph_geometry_by_composite_visible_palette():
    tokens = _tokens()
    first = _key(tokens, "#123456", ("ahead",), "a")
    second = _key(tokens, "#123456", ("behind",), "b")
    ink = RealizedGlyphInk(None, (("circle",),), (first.paint,), (10, 10))
    other_ink = replace(ink, geometry_identity=(("diamond",),), footprint=(14, 12))
    first = replace(first, glyph=ink)
    second = replace(second, glyph=other_ink)

    grouped, = legend_candidates.coalesce_actual_keys((first, second))

    assert grouped.glyph.geometry_identity == ink.geometry_identity
    assert grouped.glyph.footprint == (14, 12)
    assert grouped.variance_classes == ("ahead", "behind")
    assert grouped.ink_identity == first.ink_identity


def test_actual_grouping_mixed_scalar_and_glyph_members_is_order_safe():
    tokens = _tokens()
    scalar = _key(tokens, "#123456", ("ahead",), "scalar")
    glyph = replace(_key(tokens, "#123456", ("behind",), "glyph"),
                    glyph=RealizedGlyphInk(None, (("circle",),), (_key(tokens, "#123456").paint,), (12, 10)))

    scalar_first, = legend_candidates.coalesce_actual_keys((scalar, glyph))
    glyph_first, = legend_candidates.coalesce_actual_keys((glyph, scalar))

    assert scalar_first.glyph is None
    assert glyph_first.glyph is not None
    assert glyph_first.glyph.footprint == (12, 10)
    assert scalar_first.grouping_identity == glyph_first.grouping_identity


def test_actual_ink_identity_normalizes_implicit_and_explicit_full_opacity():
    tokens = _tokens()
    key = _key(tokens, "#123456")
    implicit = replace(key.paint, effective_channels=replace(key.paint.effective_channels, opacity=None))
    explicit = replace(key.paint, effective_channels=replace(key.paint.effective_channels, opacity=Decimal(1)))
    implicit_key = replace(key, paint=implicit)
    explicit_key = replace(key, paint=explicit)

    assert explicit_key.ink_identity == implicit_key.ink_identity


def test_final_actual_selection_keeps_premeasured_representative_geometry():
    from chrona.presentation.layout.realized_legend import _final_representative

    tokens = _tokens()
    reserved = _key(tokens, "#123456", ("ahead",), "reserved")
    realized_glyph = replace(_key(tokens, "#123456", ("behind",), "visible"),
                              glyph=RealizedGlyphInk(None, (("circle",),),
                                                     (_key(tokens, "#123456").paint,), (18, 16)))

    selected = _final_representative(reserved, realized_glyph)

    assert selected.glyph is None
    assert selected.paint is reserved.paint
    assert selected.occurrences == realized_glyph.occurrences
    assert selected.variance_classes == realized_glyph.variance_classes

    reserved_glyph = replace(reserved, glyph=RealizedGlyphInk(
        None, (("diamond",),), (reserved.paint,), (22, 20)))
    realized_scalar = _key(tokens, "#123456", ("behind",), "visible-scalar")
    selected_glyph = _final_representative(reserved_glyph, realized_scalar)
    assert selected_glyph.glyph == reserved_glyph.glyph
    assert selected_glyph.glyph.footprint == (22, 20)


def test_actual_split_labels_are_qualifier_only_for_one_class_and_base_for_ambiguous_class():
    tokens = _tokens()
    ahead = _key(tokens, "#111111", ("ahead",))
    mixed = _key(tokens, "#222222", ("ahead", "behind"))
    unclassified = _key(tokens, "#333333")
    wording = {"actual-ahead": "Early", "actual-behind": "Late"}

    assert legend_candidates.actual_key_label("Observed", ahead, multiple=True, wording=wording) == "Early"
    assert legend_candidates.actual_key_label("Observed", mixed, multiple=True, wording=wording) == "Observed"
    assert legend_candidates.actual_key_label("Observed", unclassified, multiple=True, wording=wording) == "Observed"


def test_progress_key_is_distinct_only_when_its_completed_host_actual_ink_differs(monkeypatch):
    from types import SimpleNamespace

    from chrona.presentation.layout import realized_legend

    tokens = _tokens()
    actual = _key(tokens, "#123456")
    progress = _key(tokens, "#123456", family="progressFill")
    shape = SimpleNamespace(host_placement_id="host")
    host = SimpleNamespace(placement_id="host", semantic_id="actual", mark_shape="span")
    monkeypatch.setattr(realized_legend, "actual_mark_keys", lambda *args: (actual,))
    assert not realized_legend._progress_adds_actual_ink(progress, (shape,), (host,), _content(()), tokens,
                                                         PaintWitnessCapabilities())

    distinct = _key(tokens, "#654321")
    monkeypatch.setattr(realized_legend, "actual_mark_keys", lambda *args: (distinct,))
    assert realized_legend._progress_adds_actual_ink(progress, (shape,), (host,), _content(()), tokens,
                                                     PaintWitnessCapabilities())

    shape = SimpleNamespace(host_placement_id="missing")
    assert realized_legend._progress_adds_actual_ink(progress, (shape,), (host,), _content(()), tokens,
                                                     PaintWitnessCapabilities())
