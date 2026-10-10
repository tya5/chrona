"""Axis secondary labels (#493): a second, smaller text in the same cell, measured and fitted.

Synthetic input only: nothing here reads `examples/`. The fixture font is `len(text) * size / 2` wide, so every
expected geometry below is computed independently of the code under test from that rule and the Scene's scale.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.surface_quality import AxisTierOutcome
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisSecondaryIntent, AxisTier
from chrona.presentation.model.theme_tokens import ThemeTokenError
from chrona.presentation.scene.capabilities import theme_role_contract
from chrona.presentation.scene.v05_builder import SceneBuildError
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from tests.unit.chrona.presentation.scene import test_v05_builder as base
from tests.unit.chrona.presentation.scene.test_v05_builder import _axis_tiers_scene, _theme

PRIMARY, SECONDARY = 12.0, 8.0  # px: the `axis` role (12, line 1.4) and the secondary role below
LINE = 1.4
MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS_LONG = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December")


def _theme_with(secondary_size=SECONDARY, lane=None, with_role=True, gap=None):
    """The synthetic Theme plus an `axisSecondary` text role of `secondary_size`; optionally a declared `axis` lane."""
    theme = _theme()
    body = theme["body"]
    if with_role:
        body["values"]["secondary-size"] = {"type": "number", "value": secondary_size}
        body["roles"]["axisSecondary"] = {
            "fontFamily": "body", "fontWeight": "regular", "fontSize": "secondary-size", "lineHeight": "line",
            "letterSpacing": "letter-spacing", "textTransform": "text-transform", "numericSpacing": "numeric-spacing"}
    if gap is not None:
        body["values"]["secondary-gap"] = {"type": "number", "value": gap}
        body["roles"]["axisSecondary"] = {**body["roles"]["axisSecondary"], "labelGap": "secondary-gap"}
    if lane is not None:
        body["values"]["axis-lane"] = {"type": "number", "value": lane}
        body["roles"]["axis"] = {**body["roles"]["axis"], "laneBlockSize": "axis-lane"}
    return theme


def _tier(placement="stacked", *, align="center", overflow="thin-with-record", form="short-month",
          secondary_form="short-month", secondary=True, role=None):
    intent = AxisSecondaryIntent(secondary_form, "en-US", "axisSecondary", placement) if secondary else None
    return AxisTier("month", 1, "labels",
                    AxisLabelIntent(form, (), align, overflow, "horizontal", "en-US", intent), typography_role=role)


class _Rendered:
    """A composed surface plus the typed Layout placement it came from (tier outcomes, decisions)."""

    def __init__(self, tiers, theme):
        self.surface = _axis_tiers_scene(tiers, theme=theme)
        self.placement = _composition(*tiers, theme=theme)

    def __getattr__(self, name):
        return getattr(self.surface, name)


def _scene(*tiers, theme=None):
    return _Rendered(tiers, theme or _theme_with())


def _node(surface, scene_id):
    return next(node for node in surface.primitives if node.scene_id == scene_id)


def _drawn(surface, prefix):
    return {node.scene_id: node for node in surface.primitives if node.scene_id.startswith(prefix)}


def _cell(surface, month):
    """Inline start and end of the month's cell, from the Scene's own scale."""
    scale = surface.scale_manifest
    start, end = date(2026, month, 1), date(2026 + month // 12, month % 12 + 1, 1)
    return (scale.origin + (start - scale.domain_start).days * scale.unit_ratio,
            scale.origin + (end - scale.domain_start).days * scale.unit_ratio)


def _width(text, size):
    return len(text) * size / 2


def _composition(*tiers, theme=None):
    """The Layout composition (typed tier outcomes and decisions) for the same synthetic window as `_scene`."""
    item = base.ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2027, 1, 1)}, None, None, ())
    projection = base.ReviewProjection((item,), (date(2026, 1, 1), date(2027, 1, 1)), (), ())
    measurement = base.MeasuredSources({"title": base._title_measurement()}, {"title": base.SourceInput(("Plan",))},
                                       {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
                                        "timeline.mark.blockSize": Decimal(8)})
    content = base.surface_content(axis_tiers=tiers)
    value = base.build_scene_input(projection=projection, surface_content=content,
                                   layout_manifest=base._manifest("title", "table", "timeline", "timeline-axis"),
                                   resolved_theme=theme or _theme_with(), font_metrics=base._Font(),
                                   measured_sources=measurement, capabilities={"svg": True})
    return compose_surface_layout(SurfaceLayoutRequest(
        projection=value.projection, presentation_contract=normalize_presentation_input(content),
        surface_content=content, layout_manifest=value.layout_manifest, measured_sources=value.measured_sources,
        theme_tokens=value.theme_tokens, font_metrics=value.font_metrics, capabilities=dict(value.capabilities))).placement


def _outcomes(rendered) -> AxisTierOutcome:
    return rendered.placement.axis_tier_outcomes[0]


def test_a_stacked_secondary_is_drawn_smaller_below_the_primary_in_every_cell():
    surface = _scene(_tier("stacked"))

    primaries, secondaries = _drawn(surface, "axis-label:"), _drawn(surface, "axis-label-secondary:")
    assert len(primaries) == len(secondaries) == 12
    for month, name in enumerate(MONTHS_EN, start=1):
        primary, secondary = primaries[f"axis-label:0:{month - 1}"], secondaries[f"axis-label-secondary:0:{month - 1}"]
        assert (primary.text, secondary.text) == (name, name)
        assert (primary.text_layout.font_size, secondary.text_layout.font_size) == (PRIMARY, SECONDARY)
        # The line boxes stack with no gap and no overlap; the primary keeps the top line.
        assert primary.bounds[1] == pytest.approx(0.0)
        assert secondary.bounds[1] == pytest.approx(primary.bounds[1] + primary.bounds[3])
        assert primary.bounds[3] == pytest.approx(PRIMARY * LINE)
        assert secondary.bounds[3] == pytest.approx(SECONDARY * LINE)
        # Each line is centred in the cell on its own measured width.
        start, end = _cell(surface, month)
        assert primary.bounds[2] == pytest.approx(_width(name, PRIMARY))
        assert secondary.bounds[2] == pytest.approx(_width(name, SECONDARY))
        assert primary.bounds[0] + primary.bounds[2] / 2 == pytest.approx((start + end) / 2)
        assert secondary.bounds[0] + secondary.bounds[2] / 2 == pytest.approx((start + end) / 2)
        assert secondary.visual_role == primary.visual_role


def test_a_start_aligned_stack_aligns_both_lines_at_the_cell_start():
    surface = _scene(_tier("stacked", align="start"))

    for month in range(1, 13):
        primary, secondary = _node(surface, f"axis-label:0:{month - 1}"), _node(surface, f"axis-label-secondary:0:{month - 1}")
        assert primary.bounds[0] == pytest.approx(secondary.bounds[0])


def test_an_inline_secondary_follows_the_primary_on_one_baseline_after_a_measured_space():
    surface = _scene(_tier("inline"))

    for month, name in enumerate(MONTHS_EN, start=1):
        primary, secondary = _node(surface, f"axis-label:0:{month - 1}"), _node(surface, f"axis-label-secondary:0:{month - 1}")
        space = _width(" ", PRIMARY)
        assert secondary.bounds[0] == pytest.approx(primary.bounds[0] + primary.bounds[2] + space)
        # Boxes start `size` above the baseline, so equal baselines mean top + size is equal.
        assert primary.bounds[1] + PRIMARY == pytest.approx(secondary.bounds[1] + SECONDARY)
        # The pair is centred in the cell as one unit.
        start, end = _cell(surface, month)
        pair_left, pair_right = primary.bounds[0], secondary.bounds[0] + secondary.bounds[2]
        assert (pair_left + pair_right) / 2 == pytest.approx((start + end) / 2)
        assert pair_right - pair_left == pytest.approx(_width(name, PRIMARY) + space + _width(name, SECONDARY))


def test_a_stacked_tier_grows_its_lane_by_the_secondary_line_and_pushes_the_next_tier_down():
    surface = _scene(_tier("stacked"), AxisTier("quarter", 1, "labels", AxisLabelIntent(
        "quarter", (), "center", "visible-overflow", "horizontal", "en-US"), typography_role="axis2"),
        theme=_axis2_theme())

    quarter = _node(surface, "axis-label:1:0")
    assert quarter.bounds[1] >= (PRIMARY + SECONDARY) * LINE - 1e-6


def _axis2_theme():
    theme = _theme_with()
    theme["body"]["roles"]["axis2"] = {**theme["body"]["roles"]["axis"]}
    return theme


@pytest.mark.parametrize("placement", ["stacked", "inline"])
def test_a_secondary_too_wide_for_its_cell_is_omitted_with_a_record_and_the_primary_stays(placement):
    # Long month names as the secondary at the primary's size: some cells cannot hold one.
    theme = _theme_with(secondary_size=10)
    surface = _scene(_tier(placement, secondary_form="long-month"), theme=theme)

    outcomes = _outcomes(surface).intervals
    expected_omitted = set()
    for month in range(1, 13):
        start, end = _cell(surface, month)
        secondary_width = _width(MONTHS_LONG[month - 1], 10)
        required = secondary_width if placement == "stacked" else _width(MONTHS_EN[month - 1], PRIMARY) + _width(" ", PRIMARY) + secondary_width
        if required > end - start:
            expected_omitted.add(month - 1)
    assert expected_omitted and len(expected_omitted) < 12
    for index, outcome in enumerate(outcomes):
        assert outcome.secondary_disposition == ("omitted" if index in expected_omitted else "placed")
        assert outcome.secondary_reason == ("does-not-fit" if index in expected_omitted else None)
        assert outcome.secondary_label == MONTHS_LONG[index]
        warning = f"W_LAYOUT_AXIS_SECONDARY_OMITTED:axis-label:0:{index}:does-not-fit"
        assert (warning in surface.diagnostics) == (index in expected_omitted)
        drawn = f"axis-label-secondary:0:{index}" in {node.scene_id for node in surface.primitives}
        assert drawn == (index not in expected_omitted)
        assert _node(surface, f"axis-label:0:{index}").text == MONTHS_EN[index]
    if placement == "stacked":
        # Baselines stay aligned along the axis: an omitted secondary leaves the primary on the upper line.
        assert {round(_node(surface, f"axis-label:0:{i}").bounds[1], 6) for i in range(12)} == {0.0}


def test_an_omitted_secondary_is_a_suppressed_decision_naming_the_secondary():
    surface = _scene(_tier("stacked", secondary_form="long-month"), theme=_theme_with(secondary_size=10))

    suppressed = {item.decision_id for item in surface.placement.decisions if item.outcome == "suppressed"}
    assert suppressed
    assert all(item.startswith("axis-label-secondary:0:") for item in suppressed)


def test_a_primary_that_cannot_fit_is_thinned_and_keeps_its_secondary_diagnostic():
    # Hard cell containment supersedes visible-overflow without losing the
    # earlier secondary diagnostic; neither run may paint outside the cell.
    surface = _scene(_tier("stacked", form="long-month", overflow="visible-overflow"))

    rejected = {index: outcome for index, outcome in enumerate(_outcomes(surface).intervals)
                if not outcome.label_fits}
    assert rejected
    ids = {node.scene_id for node in surface.primitives}
    for index, outcome in rejected.items():
        assert outcome.disposition == "thinned" and outcome.reason == "label-does-not-fit"
        assert outcome.secondary_label is None and outcome.secondary_disposition is None
        assert f"W_LAYOUT_AXIS_SECONDARY_OMITTED:axis-label:0:{index}:primary-does-not-fit" in surface.diagnostics
        assert f"W_LAYOUT_AXIS_LABEL_THINNED:axis-label:0:{index}:label-does-not-fit" in surface.diagnostics
        assert f"axis-label:0:{index}" not in ids and f"axis-label-secondary:0:{index}" not in ids
        decision = next(item for item in surface.placement.decisions
                        if item.decision_id == outcome.candidate_id)
        assert decision.requested_ladder == ("axis-cell-containment", "suppress")
        assert decision.outcome == "suppressed"


def test_a_thinned_primary_draws_neither_text_and_no_secondary_record():
    surface = _scene(_tier("stacked", form="long-month", overflow="thin-with-record"))

    thinned = [index for index, outcome in enumerate(_outcomes(surface).intervals) if outcome.disposition == "thinned"]
    assert thinned
    ids = {node.scene_id for node in surface.primitives}
    for index in thinned:
        assert f"axis-label:0:{index}" not in ids and f"axis-label-secondary:0:{index}" not in ids
        assert not any(item.startswith(f"W_LAYOUT_AXIS_SECONDARY_OMITTED:axis-label:0:{index}:")
                       for item in surface.diagnostics)
        assert _outcomes(surface).intervals[index].secondary_disposition is None


@pytest.mark.parametrize("placement", ["stacked", "inline"])
def test_a_secondary_never_changes_the_primarys_fit_or_thinning(placement):
    plain = _scene(_tier(placement, form="long-month", secondary=False), theme=_theme_with())
    with_secondary = _scene(_tier(placement, form="long-month", align="start"), theme=_theme_with(secondary_size=10))
    plain_start = _scene(_tier(placement, form="long-month", align="start", secondary=False), theme=_theme_with())

    def facts(surface):
        return [(item.label, item.label_fits, item.disposition, item.reason) for item in _outcomes(surface).intervals]
    assert facts(with_secondary) == facts(plain_start) == facts(plain)
    # Start-aligned primaries sit exactly where they sit without a secondary.
    for node_id, node in _drawn(plain_start, "axis-label:").items():
        assert _node(with_secondary, node_id).bounds[0] == pytest.approx(node.bounds[0])


def test_a_declared_lane_centres_the_stack_in_the_lane():
    surface = _scene(_tier("stacked"), theme=_theme_with(lane=40))

    block = (PRIMARY + SECONDARY) * LINE
    primary, secondary = _node(surface, "axis-label:0:0"), _node(surface, "axis-label-secondary:0:0")
    assert primary.bounds[1] == pytest.approx((40 - block) / 2)
    assert secondary.bounds[1] == pytest.approx((40 - block) / 2 + PRIMARY * LINE)


def test_a_declared_lane_that_cannot_hold_the_stack_is_an_error_not_a_dropped_secondary():
    with pytest.raises(SceneBuildError) as caught:
        _scene(_tier("stacked"), theme=_theme_with(lane=20))

    assert (caught.value.diagnostic_id, caught.value.detail) == ("E_PRESENTATION_AXIS_OVERFLOW", "secondary-lane:0")


def test_a_lane_that_holds_the_inline_line_but_not_the_stack_is_allowed_inline():
    # 20 px holds one 16.8 px line (inline), not 16.8 + 11.2 (stacked).
    assert _scene(_tier("inline"), theme=_theme_with(lane=20)) is not None
    with pytest.raises(SceneBuildError):
        _scene(_tier("stacked"), theme=_theme_with(lane=20))


def test_a_stack_taller_than_the_axis_slot_is_an_error():
    with pytest.raises(SceneBuildError) as caught:
        _scene(_tier("stacked"), theme=_theme_with(secondary_size=40))

    assert (caught.value.diagnostic_id, caught.value.detail) == ("E_PRESENTATION_AXIS_OVERFLOW", "secondary-lane:0")


def test_a_theme_without_the_secondary_role_fails_with_a_token_error_not_a_fallback():
    with pytest.raises(ThemeTokenError):
        _scene(_tier("stacked"), theme=_theme_with(with_role=False))


def test_the_secondary_role_is_admitted_as_an_axis_typography_role():
    assert theme_role_contract("axisSecondary") is not None
    assert "fontSize" in theme_role_contract("axisSecondary").properties


def test_the_secondary_form_is_formatted_by_its_own_name_table():
    surface = _scene(AxisTier("month", 1, "labels", AxisLabelIntent(
        "short-month", (), "center", "thin-with-record", "horizontal", "en-US",
        AxisSecondaryIntent("short-month", "ja-JP", "axisSecondary", "inline"))))

    assert [_node(surface, f"axis-label-secondary:0:{i}").text for i in range(3)] == ["1月", "2月", "3月"]
    assert [_node(surface, f"axis-label:0:{i}").text for i in range(3)] == ["Jan", "Feb", "Mar"]


def test_a_noncanonical_secondary_form_is_reported_like_a_primary_one():
    surface = _scene(AxisTier("month", 1, "labels", AxisLabelIntent(
        "short-month", (), "center", "thin-with-record", "horizontal", "en-US",
        AxisSecondaryIntent("long-month", "en-US", "axisSecondary", "stacked"))), theme=_theme_with(secondary_size=6))

    assert any(item.startswith("W_LAYOUT_AXIS_FORM_EQUIVALENT:axis-label-secondary:0:4:table=en-US:form=long-month:")
               for item in surface.diagnostics)


def test_without_a_secondary_the_axis_is_primitive_for_primitive_unchanged():
    # The Theme has no `axisSecondary` role at all: a tier without a secondary must never resolve it.
    surface = _scene(_tier("stacked", secondary=False), theme=_theme_with(with_role=False))

    assert not _drawn(surface, "axis-label-secondary:")
    assert all(outcome.secondary_disposition is None and outcome.secondary_label is None
               for outcome in _outcomes(surface).intervals)
    assert not any("SECONDARY" in item for item in surface.diagnostics)
    for month, name in enumerate(MONTHS_EN, start=1):
        node = _node(surface, f"axis-label:0:{month - 1}")
        start, end = _cell(surface, month)
        assert node.text == name
        assert node.bounds == pytest.approx((start + (end - start - _width(name, PRIMARY)) / 2, 0.0,
                                             _width(name, PRIMARY), PRIMARY * LINE))


def test_a_declared_gap_opens_a_stacked_pair_by_a_ratio_of_the_secondary_size():
    surface = _scene(_tier("stacked"), theme=_theme_with(gap=0.5))

    primary, secondary = _node(surface, "axis-label:0:0"), _node(surface, "axis-label-secondary:0:0")
    assert secondary.bounds[1] == pytest.approx(primary.bounds[1] + primary.bounds[3] + 0.5 * SECONDARY)


def test_a_declared_gap_replaces_the_inline_default_space():
    surface = _scene(_tier("inline"), theme=_theme_with(gap=0.75))

    primary, secondary = _node(surface, "axis-label:0:0"), _node(surface, "axis-label-secondary:0:0")
    assert secondary.bounds[0] == pytest.approx(primary.bounds[0] + primary.bounds[2] + 0.75 * SECONDARY)


def test_the_gap_counts_toward_the_fit_and_the_lane():
    # A gap large enough that the pair no longer fits the narrowest cell omits the secondary there.
    narrow = _scene(_tier("inline", align="start"), theme=_theme_with(gap=0.0))
    wide = _scene(_tier("inline", align="start"), theme=_theme_with(gap=6.0))
    assert all(item.secondary_disposition == "placed" for item in _outcomes(narrow).intervals)
    assert any(item.secondary_reason == "does-not-fit" for item in _outcomes(wide).intervals)
    with pytest.raises(SceneBuildError) as caught:
        _scene(_tier("stacked"), theme=_theme_with(lane=30, gap=1.0))
    assert caught.value.detail == "secondary-lane:0"


def test_a_negative_gap_is_diagnosed_not_clamped():
    with pytest.raises(SceneBuildError) as caught:
        _scene(_tier("inline"), theme=_theme_with(gap=-0.1))

    assert (caught.value.diagnostic_id, caught.value.detail) == ("E_PRESENTATION_AXIS_INVALID", "label-gap:axisSecondary")


def test_label_gap_is_admitted_on_the_axis_roles_only():
    for role in ("axis", "axisMonth", "axisSecondary"):
        assert "labelGap" in theme_role_contract(role).properties
    for role in ("text", "heading", "axis-rule", "planned"):
        assert "labelGap" not in theme_role_contract(role).properties
