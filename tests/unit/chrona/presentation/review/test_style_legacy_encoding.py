"""Legacy View color encodings lower to shared Style intent without changing eligibility."""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.model.color_scale import ColorScaleError, ResolvedColorScale
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.style_rules import (
    StyleFieldFact, StyleOccurrence, StyleOccurrenceKey, evaluate_style_rules,
)
from chrona.presentation.review.style_intent import lower_legacy_color_encoding
from chrona.presentation.review.v05_content import normalize_v05_surface_content
from chrona.presentation.style import StyleEncodingOutcome, StyleFieldSource, StyleSelector
from chrona.presentation.contracts.resources import (
    ViewComparison, ViewInput, ViewRows, ViewVisibility, ViewWindow,
)
from chrona.presentation.model.surface_content import SummaryContent


def _encoding(target: str = "planned", *, domain: list[str] | str = "firstAppearance") -> dict:
    return {
        "scale": "legacy-category", "target": target,
        "source": {"field": "phase"}, "domain": domain,
    }


def _occurrence(semantic: str, *, value: str = "build") -> StyleOccurrence:
    binding = semantic_binding(semantic)
    return StyleOccurrence(
        StyleOccurrenceKey(semantic, "primary", semantic),
        binding.purpose,
        binding.primitive_kind,
        fields=(StyleFieldFact("phase", None, True, value),),
    )


def test_planned_encoding_eligibility_matches_host_role_not_shared_purpose():
    rules = lower_legacy_color_encoding(_encoding())

    assert tuple(rule.selector.semantic for rule in rules) == ("planned", "forecast")
    assert all(rule.selector == StyleSelector(semantic=rule.selector.semantic) for rule in rules)
    assert all(rule.rule_id == f"view-colorEncoding:{rule.selector.semantic}" for rule in rules)
    assert all(rule.source_ref == "/body/colorEncoding" for rule in rules)
    # A gate has purpose=planned but its canonical Scene role is gate, so it is not eligible.
    assert semantic_binding("gate").purpose == semantic_binding("planned").purpose
    assert semantic_binding("gate").scene_role != "planned"

    occurrences = tuple(_occurrence(semantic) for semantic in ("planned", "forecast", "gate", "actual", "snapshot"))
    intents = evaluate_style_rules(rules, occurrences)

    assert tuple(intent.key.semantic_id for intent in intents) == ("planned", "forecast")
    assert all(intent.fill is not None for intent in intents)
    assert all(intent.fill.source == StyleFieldSource(field_name="phase") for intent in intents)
    assert all(intent.fill.scale_id == "legacy-category" for intent in intents)
    assert all(intent.fill.domain == "firstAppearance" and intent.fill.legend is None for intent in intents)


@pytest.mark.parametrize(
    ("domain", "expected"),
    [(["PDR", "CDR", "PSR"], ("PDR", "CDR", "PSR")), ("firstAppearance", "firstAppearance")],
)
def test_lowering_retains_explicit_or_first_appearance_domain(domain, expected):
    (rule,) = lower_legacy_color_encoding(_encoding("actual", domain=domain))

    assert rule.selector.semantic == "actual"
    assert isinstance(rule.outcome, StyleEncodingOutcome)
    assert rule.outcome.domain == expected
    assert rule.outcome.legend is None


def test_legacy_encoding_accepts_opaque_field_facts_without_a_style_predicate():
    rule = next(rule for rule in lower_legacy_color_encoding(_encoding("planned"))
                if rule.selector.semantic == "planned")
    occurrence = _occurrence("planned", value="custom-kind")

    (intent,) = evaluate_style_rules((rule,), (occurrence,))

    assert intent.fill is not None
    assert intent.fill.source.field_name == "phase"
    assert intent.fill.legend is None  # legacy input does not acquire scoped-Style legend requirements


def test_absent_legacy_color_encoding_lowers_to_no_rules():
    assert lower_legacy_color_encoding(None) == ()


def _surface_view() -> ViewInput:
    return ViewInput(
        None, None, None, ViewWindow("selected-planned", None, None, 0),
        ViewComparison(None, "optional", None, None, ()),
        ViewVisibility(False, "none", "none"), (), (), ViewRows("automatic", ()),
        None, (), None, None, None,
    )


def _surface_item(object_id: str, *, value: str | None, source_kind: str = "primary") -> ReviewItem:
    fields = {} if value is None else {"phase": value}
    return ReviewItem(
        object_id, object_id.upper(), "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
        None, None, ("planned",), fields=fields, source_kind=source_kind,
    )


def _surface_content(items: tuple[ReviewItem, ...], scale: ResolvedColorScale):
    projection = ReviewProjection(items, (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    return normalize_v05_surface_content(
        projection, {"relations": (), "annotations": {}}, _surface_view(),
        summary=SummaryContent(()), color_scale=scale,
    )


def test_v05_surface_color_intent_preserves_source_order_and_excludes_non_primary_sources():
    scale = ResolvedColorScale(
        "phase", "planned", "phase", ("review", "build"),
        (("review", "#112233"), ("build", "#445566")),
    )

    content = _surface_content((
        _surface_item("second", value="build"),
        _surface_item("snapshot", value="review", source_kind="snapshot"),
        _surface_item("first", value="review", source_kind="combined"),
    ), scale)

    assert content.scale_paints == (("second", "#445566"), ("first", "#112233"))


def test_v05_surface_first_appearance_scale_omits_items_missing_the_derived_field():
    scale = ResolvedColorScale(
        "phase", "planned", "phase", ("build",), (("build", "#445566"),), derived=True,
    )

    content = _surface_content((
        _surface_item("missing", value=None),
        _surface_item("present", value="build"),
    ), scale)

    assert content.scale_paints == (("present", "#445566"),)


def test_v05_surface_explicit_scale_still_reports_an_item_missing_its_field():
    scale = ResolvedColorScale(
        "phase", "planned", "phase", ("build",), (("build", "#445566"),),
    )

    with pytest.raises(ColorScaleError) as error:
        _surface_content((_surface_item("missing", value=None),), scale)

    assert error.value.code == "E_PRESENTATION_SCALE_VALUE"
    assert error.value.source_ref == "/body/colorEncoding"
