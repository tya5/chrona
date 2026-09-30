from decimal import ROUND_CEILING, Decimal
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.engine import (_unresolved_normal_flow_warnings,
                                               measure_natural_normal_flow_block,
                                               resolve_content_block_extent, solve_layout)
from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.layout.profile import resolve_layout_profile


ROOT = Path(__file__).parents[5]
PROFILES = ROOT / "tests/fixtures/layout-profiles"
SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}


def profile():
    value = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    return resolve_layout_profile(value, available_sources=SOURCES, theme={"body": {"values": values}})


def m(i, b, *, baseline=None):
    return Measurement(Decimal(i)/2, Decimal(i), Decimal(i)*2, Decimal(b)/2, Decimal(b), Decimal(b)*2,
                       None if baseline is None else Decimal(baseline), None if baseline is None else Decimal(baseline))


MEASUREMENTS = {
    "title": m(300, 40), "table": m(300, 600), "timeline-axis": m(500, 50),
    "timeline": m(500, 600), "legend": m(240, 32, baseline=24), "notes": m(300, 32, baseline=20),
}


def decisions(manifest):
    return {item.node_id: item.bounds for item in manifest.decisions}


def test_center_fraction_content_and_baseline_reflow_without_author_coordinates():
    first = solve_layout(profile(), viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS)
    second = solve_layout(profile(), viewport_inline=1200, viewport_block=900, measurements=MEASUREMENTS)
    a, b = decisions(first), decisions(second)
    assert a["title"].inline == (Decimal(1600) - a["title"].inline_size) / 2
    assert b["title"].inline == (Decimal(1200) - b["title"].inline_size) / 2
    assert a["timeline-stack"].inline_size > a["table"].inline_size
    assert a["legend"].block + 24 == a["notes"].block + 20
    assert first.canonical_bytes() == solve_layout(profile(), viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS).canonical_bytes()


def test_content_requirement_reallocates_the_whole_normal_flow_profile():
    resolved = profile()
    required = Decimal(850)
    extent = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=900,
                                          measurements=MEASUREMENTS,
                                          required_blocks={"timeline": required})
    assert extent.extent > 900
    assert not extent.short_sources
    placed = decisions(solve_layout(resolved, viewport_inline=1600, viewport_block=extent.extent,
                                    measurements=MEASUREMENTS))
    assert placed["timeline"].block_size >= required
    assert placed["table"].block + placed["table"].block_size == (
        placed["timeline"].block + placed["timeline"].block_size)
    assert placed["notes"].block >= placed["table"].block + placed["table"].block_size


def test_auto_content_sizing_uses_positive_floor_and_rounds_deterministically():
    resolved = profile()
    required = Decimal("300.2")
    natural_floor = max(1, int(measure_natural_normal_flow_block(
        resolved, viewport_inline=1600, measurements=MEASUREMENTS
    ).to_integral_value(rounding="ROUND_CEILING")))
    first = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=natural_floor,
                                        measurements=MEASUREMENTS,
                                        required_blocks={"timeline": required}, content_sized=True)
    second = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=natural_floor,
                                         measurements=MEASUREMENTS,
                                         required_blocks={"timeline": required}, content_sized=True)
    assert 0 < first.extent < 900
    assert first.extent == second.extent
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=first.extent,
                            measurements=MEASUREMENTS)
    assert decisions(manifest)["timeline"].block_size >= required


def test_finite_900_minimum_and_profile_intrinsic_minimum_are_preserved():
    resolved = profile()
    finite = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=900,
                                          measurements=MEASUREMENTS,
                                          required_blocks={"timeline": Decimal(300)})
    assert finite.extent == 900
    auto_measurements = dict(MEASUREMENTS)
    auto_measurements["title"] = m(300, 1400)
    natural_floor = int(measure_natural_normal_flow_block(
        resolved, viewport_inline=1600, measurements=auto_measurements
    ).to_integral_value(rounding="ROUND_CEILING"))
    auto = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=natural_floor,
                                        measurements=auto_measurements,
                                        required_blocks={"timeline": Decimal(300)}, content_sized=True)
    assert auto.extent > 900
    placed = decisions(solve_layout(resolved, viewport_inline=1600, viewport_block=auto.extent,
                                    measurements=auto_measurements))
    assert placed["title"].block_size >= Decimal(700)


def test_auto_content_requirement_above_900_expands_beyond_intrinsic_floor():
    resolved = profile()
    floor = int(measure_natural_normal_flow_block(
        resolved, viewport_inline=1600, measurements=MEASUREMENTS
    ).to_integral_value(rounding="ROUND_CEILING"))
    result = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=floor,
                                          measurements=MEASUREMENTS,
                                          required_blocks={"timeline": Decimal(850)},
                                          content_sized=True)
    assert result.extent > 900
    placed = decisions(solve_layout(resolved, viewport_inline=1600, viewport_block=result.extent,
                                    measurements=MEASUREMENTS))
    assert placed["timeline"].block_size >= Decimal(850)


def test_auto_block_growth_ignores_unrelated_inline_only_overflow():
    resolved = profile()
    measurements = dict(MEASUREMENTS)
    measurements["title"] = Measurement(
        Decimal(2000), Decimal(3000), Decimal(4000),
        Decimal(20), Decimal(40), Decimal(60),
    )
    floor = max(1, int(measure_natural_normal_flow_block(
        resolved, viewport_inline=1600, measurements=measurements,
    ).to_integral_value(rounding=ROUND_CEILING)))
    at_floor = solve_layout(resolved, viewport_inline=1600, viewport_block=floor,
                            measurements=measurements, content_sized=True)
    assert any(warning.placement_id == "title"
               and warning.required_inline > warning.available_inline
               and warning.required_block <= warning.available_block
               for warning in at_floor.fit_warnings)
    result = resolve_content_block_extent(
        resolved, viewport_inline=1600, minimum_block=floor, measurements=measurements,
        required_blocks={"timeline": Decimal(850)}, content_sized=True,
    )
    assert result.extent > floor
    assert not result.short_sources
    final = solve_layout(resolved, viewport_inline=1600, viewport_block=result.extent,
                         measurements=measurements, content_sized=True)
    assert decisions(final)["timeline"].block_size >= Decimal(850)


def test_auto_empty_requirement_uses_one_unit_floor_and_unknown_source_fails():
    resolved = profile()
    empty_measurements = {source: m(0, 0, baseline=0) for source in SOURCES}
    natural_floor = int(measure_natural_normal_flow_block(
        resolved, viewport_inline=1600, measurements=empty_measurements
    ).to_integral_value(rounding="ROUND_CEILING"))
    empty = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=max(1, natural_floor),
                                         measurements=empty_measurements, required_blocks={},
                                         content_sized=True)
    assert 0 < empty.extent < 900
    with pytest.raises(LayoutError, match="E_LAYOUT_DRAFT_AUTO_UNSUPPORTED"):
        resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=1,
                                     measurements=MEASUREMENTS,
                                     required_blocks={"missing": Decimal(2)}, content_sized=True)


def test_natural_grid_requirement_sums_single_span_track_bases_and_keeps_span_overflow():
    raw = yaml.safe_load((PROFILES / "print-portrait.yaml").read_text(encoding="utf-8"))
    tokens = {name: {"type": "number", "value": value} for name, value in {
        "panel.timeline": 200, "spacing.m": 16, "spacing.none": 0, "spacing.xl": 32,
    }.items()}
    resolved = resolve_layout_profile(raw, available_sources=SOURCES,
                                      theme={"body": {"values": tokens}})
    natural = measure_natural_normal_flow_block(resolved, viewport_inline=1600, measurements=MEASUREMENTS)
    assert natural == Decimal(416)

    # Notes spans both columns, so its oversized inline requirement remains
    # visible overflow and does not invent extra grid row height.
    oversized = dict(MEASUREMENTS)
    oversized["notes"] = Measurement(Decimal(2000), Decimal(4000), Decimal(5000),
                                     Decimal(16), Decimal(32), Decimal(64),
                                     Decimal(20), Decimal(20))
    same_natural = measure_natural_normal_flow_block(resolved, viewport_inline=1600,
                                                     measurements=oversized)
    assert same_natural == natural
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=int(natural),
                            measurements=oversized)
    assert any(warning.placement_id == "notes" for warning in manifest.fit_warnings)


def test_capped_minmax_grid_row_warning_is_valid_fallback_for_auto_closure():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    child = {"id": "capped-child", "kind": "slot", "source": "title",
             "inlineSize": "fill", "blockSize": "content",
             "place": {"inline": "start", "block": "start", "safety": "safe"},
             "priority": "required", "overflow": "visible-overflow",
             "cell": {"column": 1, "row": 1}}
    raw["root"].update(
        kind="grid", columnTracks=["fill"],
        rowTracks=[{"minmax": {"min": "content", "max": {"fixed": 180}}}, "fill"],
        alignItems="stretch", justifyContent="start", children=[child],
    )
    raw["requiredThemeTokens"] = ["spacing.l", "spacing.m"]
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16,
        "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    resolved = resolve_layout_profile(raw, available_sources={"title"},
                                      theme={"body": {"values": values}})
    measured = {"capped-child": m(300, 400)}
    natural = measure_natural_normal_flow_block(resolved, viewport_inline=1600, measurements=measured)
    assert natural == Decimal(244)
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=int(natural),
                            measurements=measured, content_sized=True)
    assert any(warning.placement_id == "capped-child" for warning in manifest.fit_warnings)
    assert not _unresolved_normal_flow_warnings(resolved, manifest)


def test_nested_grid_measurement_sums_rows_for_outer_content_track():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    title = {"id": "nested-title", "kind": "slot", "source": "title",
             "inlineSize": "fill", "blockSize": "content",
             "place": {"inline": "start", "block": "start", "safety": "safe"},
             "priority": "required", "overflow": "visible-overflow",
             "cell": {"column": 1, "row": 1}}
    notes = {"id": "nested-notes", "kind": "slot", "source": "notes",
             "inlineSize": "fill", "blockSize": "content",
             "place": {"inline": "start", "block": "start", "safety": "safe"},
             "priority": "required", "overflow": "visible-overflow",
             "cell": {"column": 1, "row": 2}}
    spanning = {"id": "nested-spanning", "kind": "slot", "source": "timeline",
                "inlineSize": "fill", "blockSize": "content",
                "place": {"inline": "start", "block": "start", "safety": "safe"},
                "priority": "required", "overflow": "visible-overflow",
                "cell": {"column": 1, "row": 1, "rowSpan": 2}}
    root_spanning = {"id": "root-spanning", "kind": "slot", "source": "legend",
                     "inlineSize": "fill", "blockSize": "content",
                     "place": {"inline": "start", "block": "start", "safety": "safe"},
                     "priority": "required", "overflow": "visible-overflow",
                     "cell": {"column": 1, "row": 1, "rowSpan": 2}}
    nested = {"id": "nested-grid", "kind": "grid", "inlineSize": "fill",
              "blockSize": "content", "columnTracks": ["fill"],
              "rowTracks": ["content", "content"], "gap": {"token": "spacing.m"},
              "padding": {"token": "spacing.none"}, "alignItems": "stretch",
              "justifyContent": "start",
              "children": [title, notes, spanning]}
    raw["root"].update(kind="grid", columnTracks=["fill"], rowTracks=["content", {"fixed": 0}],
                        alignItems="stretch", justifyContent="start", children=[nested, root_spanning])
    raw["requiredThemeTokens"] = ["spacing.l", "spacing.m", "spacing.none"]
    nested["cell"] = {"column": 1, "row": 1}
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16,
        "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    resolved = resolve_layout_profile(raw, available_sources={"title", "notes", "timeline", "legend"},
                                      theme={"body": {"values": values}})
    nested_measurements = {**MEASUREMENTS, "nested-title": MEASUREMENTS["title"],
                          "nested-notes": MEASUREMENTS["notes"],
                          "nested-spanning": m(300, 1800),
                          "root-spanning": m(300, 2200)}
    natural = measure_natural_normal_flow_block(resolved, viewport_inline=1600,
                                               measurements=nested_measurements)
    assert natural == Decimal(152)
    larger = dict(MEASUREMENTS)
    larger["title"] = m(300, 400)
    larger["notes"] = m(300, 300)
    larger["nested-title"] = larger["title"]
    larger["nested-notes"] = larger["notes"]
    larger["nested-spanning"] = m(300, 2400)
    larger["root-spanning"] = m(300, 2800)
    larger_natural = measure_natural_normal_flow_block(resolved, viewport_inline=1600,
                                                       measurements=larger)
    assert larger_natural == Decimal(780)
    placed = solve_layout(resolved, viewport_inline=1600, viewport_block=int(larger_natural),
                          measurements=larger, content_sized=True)
    nested_bounds = decisions(placed)["nested-grid"]
    assert nested_bounds.block_size == larger_natural - 64
    assert {warning.placement_id for warning in placed.fit_warnings} == {
        "nested-spanning", "root-spanning",
    }
    auto = resolve_content_block_extent(
        resolved, viewport_inline=1600, minimum_block=int(larger_natural),
        measurements=larger, required_blocks={"timeline": Decimal(600)}, content_sized=True,
    )
    assert auto.extent == larger_natural


def test_natural_flow_requirement_wraps_at_resolved_inline_width():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    raw["root"]["children"] = [raw["root"]["children"][2]]
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16,
        "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    resolved = resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    wide = measure_natural_normal_flow_block(resolved, viewport_inline=800, measurements=MEASUREMENTS)
    narrow = measure_natural_normal_flow_block(resolved, viewport_inline=400, measurements=MEASUREMENTS)
    assert narrow > wide


def test_anchored_overlay_decoration_does_not_increase_natural_flow_floor():
    raw = yaml.safe_load((PROFILES / "overlay-briefing.yaml").read_text(encoding="utf-8"))
    tokens = {name: {"type": "number", "value": value} for name, value in {
        "panel.review.block": 200, "panel.side": 240, "spacing.l": 24,
        "spacing.m": 16, "spacing.none": 0,
    }.items()}
    raw["root"]["blockSize"] = "content"
    resolved = resolve_layout_profile(raw, available_sources=SOURCES,
                                      theme={"body": {"values": tokens}})
    # Exercise the content-sized overlay intrinsic path: anchored panel content
    # must not set the root's normal-flow floor through `_measure_node`.
    baseline = measure_natural_normal_flow_block(resolved, viewport_inline=1600,
                                                 measurements=MEASUREMENTS)
    larger = dict(MEASUREMENTS)
    larger["timeline"] = m(500, 2000)
    assert measure_natural_normal_flow_block(resolved, viewport_inline=1600,
                                             measurements=larger) == baseline


def test_content_requirement_does_not_inflate_a_fixed_timeline_host():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    raw["root"]["children"][1]["children"][1]["children"][1]["blockSize"] = {"fixed": 800}
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24,
        "panel.minimum": 180,
    }.items()}
    resolved = resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    result = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=900,
                                          measurements=MEASUREMENTS,
                                          required_blocks={"timeline": Decimal(850)})
    assert result.extent == 900
    assert len(result.short_sources) == 1
    assert result.short_sources[0].source_id == "timeline"
    assert result.short_sources[0].required_block == Decimal(850)
    assert result.short_sources[0].allocated_block < Decimal(850)

    auto_floor = int(measure_natural_normal_flow_block(
        resolved, viewport_inline=1600, measurements=MEASUREMENTS
    ).to_integral_value(rounding="ROUND_CEILING"))
    auto = resolve_content_block_extent(resolved, viewport_inline=1600, minimum_block=auto_floor,
                                        measurements=MEASUREMENTS,
                                        required_blocks={"timeline": Decimal(850)},
                                        content_sized=True)
    assert auto.extent == auto_floor
    assert auto.short_sources == result.short_sources


def test_content_change_recenters_title():
    changed = dict(MEASUREMENTS); changed["title"] = m(500, 40)
    before=decisions(solve_layout(profile(),viewport_inline=1600,viewport_block=900,measurements=MEASUREMENTS))["title"]
    after=decisions(solve_layout(profile(),viewport_inline=1600,viewport_block=900,measurements=changed))["title"]
    assert after.inline < before.inline and after.inline_size > before.inline_size


def test_missing_measurement_rejects_but_valid_shortage_completes_with_warning():
    missing=dict(MEASUREMENTS); del missing["title"]
    with pytest.raises(LayoutError,match="E_LAYOUT_MEASUREMENT_REQUIRED"):
        solve_layout(profile(),viewport_inline=1600,viewport_block=900,measurements=missing)
    narrow = solve_layout(profile(), viewport_inline=300, viewport_block=100, measurements=MEASUREMENTS)
    assert narrow.fit_warnings
    assert all(warning.code == "W_LAYOUT_VISIBLE_OVERFLOW" for warning in narrow.fit_warnings)
    assert any(warning.required_inline > warning.available_inline or
               warning.required_block > warning.available_block for warning in narrow.fit_warnings)


def test_layout_token_requirement_contract_is_exact_and_theme_checked():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    theme = {"body": {"values": {"spacing.none": {"type": "number", "value": 0},
                                  "spacing.m": {"type": "number", "value": 16},
                                  "spacing.l": {"type": "number", "value": 24},
                                  "panel.minimum": {"type": "number", "value": 180}}}}
    raw["requiredThemeTokens"].remove("spacing.m")
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_REQUIREMENT_MISSING"):
        resolve_layout_profile(raw, available_sources=SOURCES, theme=theme)
    raw["requiredThemeTokens"].append("spacing.m")
    raw["requiredThemeTokens"].append("spacing.xl")
    raw["requiredThemeTokens"].sort()
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_REQUIREMENT_EXTRANEOUS"):
        resolve_layout_profile(raw, available_sources=SOURCES, theme=theme)
    raw["requiredThemeTokens"].remove("spacing.xl")
    del theme["body"]["values"]["panel.minimum"]
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE"):
        resolve_layout_profile(raw, available_sources=SOURCES, theme=theme)
    theme["body"]["values"]["panel.minimum"] = {"type": "color", "value": "#000000"}
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_REQUIREMENT_TYPE"):
        resolve_layout_profile(raw, available_sources=SOURCES, theme=theme)


def test_unavailable_optional_source_does_not_participate_in_layout():
    raw = {
        "version": "chrona/layout-profile/v0.9", "id": "optional-source", "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": ["spacing.m", "spacing.none"], "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {"rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"}, "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
        "root": {"id": "root", "kind": "column", "inlineSize": "fill", "blockSize": "fill",
                 "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
                 "alignItems": "stretch", "justifyContent": "start", "children": [
                     {"id": "title", "kind": "slot", "source": "title", "inlineSize": "content", "blockSize": "content",
                      "place": {"inline": "start", "block": "start", "safety": "strict"}, "priority": "required", "overflow": "visible-overflow"},
                     {"id": "annotations", "kind": "slot", "source": "annotations", "inlineSize": "content", "blockSize": "content",
                      "place": {"inline": "start", "block": "start", "safety": "strict"}, "priority": "optional", "overflow": "visible-overflow"},
                 ]},
    }
    theme = {"body": {"values": {"spacing.m": {"type": "number", "value": 16},
                                    "spacing.none": {"type": "number", "value": 0}}}}
    resolved = resolve_layout_profile(raw, available_sources={"title"}, theme=theme)
    result = decisions(solve_layout(resolved, viewport_inline=800, viewport_block=300,
                                    measurements={"title": MEASUREMENTS["title"]}))
    assert "annotations" not in result
    assert result["title"].block == 0


def test_grid_and_distribution_are_deterministic():
    raw={
      "version":"chrona/layout-profile/v0.9","id":"grid","flowDirection":"horizontal","dependencyNetworkFlowDirection":"horizontal","requiredThemeTokens":["spacing.m","spacing.none"],"reviewSurface":{"rowDistribution":"pack","backgroundExtents":{"rowBand":"table","groupBand":"timeline","groupHeaderBand":"both","calendarClosed":"timeline"},"annotationRouting":{"maxBends":4,"maxDetourRatio":2}},
      "root":{"id":"root","kind":"grid","inlineSize":"fill","blockSize":"fill","columnTracks":[{"fr":1},{"fr":1}],"rowTracks":["content"],"gap":{"token":"spacing.m"},"padding":{"token":"spacing.none"},"alignItems":"stretch","justifyContent":"start","children":[
        {"id":"legend","kind":"slot","source":"legend","inlineSize":"fill","blockSize":"content","place":{"inline":"stretch","block":"start","safety":"strict"},"priority":"required","overflow":"visible-overflow","cell":{"column":1,"row":1}},
        {"id":"notes","kind":"slot","source":"notes","inlineSize":"fill","blockSize":"content","place":{"inline":"stretch","block":"start","safety":"strict"},"priority":"required","overflow":"visible-overflow","cell":{"column":2,"row":1}}
      ]}}
    theme={"body":{"values":{"spacing.m":{"type":"number","value":16},"spacing.none":{"type":"number","value":0}}}}
    resolved=resolve_layout_profile(raw,available_sources={"legend","notes"},theme=theme)
    result=decisions(solve_layout(resolved,viewport_inline=1000,viewport_block=100,measurements={"legend":MEASUREMENTS["legend"],"notes":MEASUREMENTS["notes"]}))
    assert result["legend"].inline_size == result["notes"].inline_size == Decimal(492)
    assert result["notes"].inline == Decimal(508)
    narrow = solve_layout(resolved, viewport_inline=200, viewport_block=20,
                          measurements={"legend": MEASUREMENTS["legend"], "notes": MEASUREMENTS["notes"]})
    assert any(warning.placement_id == "root" and warning.required_block > warning.available_block
               for warning in narrow.fit_warnings)
    assert all(item.bounds.inline_size >= 0 and item.bounds.block_size >= 0 for item in narrow.decisions)


def test_review_surface_requires_the_closed_background_extent_mapping():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    del raw["reviewSurface"]["backgroundExtents"]["rowBand"]
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as error:
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    assert error.value.path == "/reviewSurface/backgroundExtents"


def test_v09_requires_annotation_routing_and_rejects_the_removed_v08_identity():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    del raw["reviewSurface"]["annotationRouting"]
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as error:
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    assert error.value.path == "/reviewSurface"

    raw["version"] = "chrona/layout-profile/v0.7"
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as error:
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    assert error.value.path == "/version"


def test_v08_rejects_misleading_writing_mode_and_invalid_network_direction():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    raw["writingMode"] = "vertical-rl"
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    raw.pop("writingMode")
    raw["dependencyNetworkFlowDirection"] = "diagonal"
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})


def test_annotation_routing_is_manifested_independently_of_relation_routing():
    raw = yaml.safe_load((PROFILES / "briefing.yaml").read_text(encoding="utf-8"))
    raw["reviewSurface"]["annotationRouting"] = {"maxBends": 1, "maxDetourRatio": 1}
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    resolved = resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS)
    assert (manifest.annotation_max_bends, manifest.annotation_max_detour_ratio) == (1, 1.0)
    assert (manifest.relation_max_bends, manifest.relation_max_detour_ratio) == (4, 2.0)
    assert b'"annotationRouting":{"maxBends":1,"maxDetourRatio":1.0}' in manifest.canonical_bytes()


def relative_profile():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-relative-v0.2.yaml").read_text(encoding="utf-8"))
    theme = {"body": {"values": {
        "spacing.l": {"type": "number", "value": 24},
        "spacing.m": {"type": "number", "value": 16},
    }}}
    return resolve_layout_profile(raw, available_sources=SOURCES | {"group-details", "observations", "milestones"}, theme=theme)


RELATIVE_MEASUREMENTS = {
    "group-details": m(280, 80),
    "observations": m(360, 120),
    "milestones": m(200, 60),
}


def test_axis_specific_barrier_and_parent_anchor_reflow():
    first = solve_layout(relative_profile(), viewport_inline=1000, viewport_block=500, measurements=RELATIVE_MEASUREMENTS)
    result = decisions(first)
    barrier = max(result["group-details"].inline + result["group-details"].inline_size,
                  result["observations"].inline + result["observations"].inline_size)
    assert result["milestones"].inline == barrier + 16
    assert result["milestones"].block + result["milestones"].block_size / 2 == Decimal(250)
    milestone = next(item for item in first.decisions if item.node_id == "milestones")
    assert milestone.references == ("barrier:label-end", "parent")

    changed = deepcopy(RELATIVE_MEASUREMENTS)
    changed["observations"] = m(500, 120)
    after = decisions(solve_layout(relative_profile(), viewport_inline=1000, viewport_block=500, measurements=changed))
    assert after["milestones"].inline > result["milestones"].inline


def test_relative_manifest_is_deterministic():
    first = solve_layout(relative_profile(), viewport_inline=1000, viewport_block=500, measurements=RELATIVE_MEASUREMENTS)
    second = solve_layout(relative_profile(), viewport_inline=1000, viewport_block=500, measurements=RELATIVE_MEASUREMENTS)
    assert first.canonical_bytes() == second.canonical_bytes()


def test_narrow_relative_overlay_preserves_child_placement_and_warns():
    manifest = solve_layout(relative_profile(), viewport_inline=200, viewport_block=100,
                            measurements=RELATIVE_MEASUREMENTS)
    placed = decisions(manifest)
    assert "milestones" in placed
    assert manifest.fit_warnings
    assert any(warning.placement_id == "milestones" for warning in manifest.fit_warnings)
