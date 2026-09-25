from decimal import Decimal
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import LayoutError, Measurement
from chrona.presentation.layout.profile import resolve_layout_profile


ROOT = Path(__file__).parents[5]
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


def test_content_change_recenters_title():
    changed = dict(MEASUREMENTS); changed["title"] = m(500, 40)
    before=decisions(solve_layout(profile(),viewport_inline=1600,viewport_block=900,measurements=MEASUREMENTS))["title"]
    after=decisions(solve_layout(profile(),viewport_inline=1600,viewport_block=900,measurements=changed))["title"]
    assert after.inline < before.inline and after.inline_size > before.inline_size


def test_missing_measurement_and_required_overflow_diagnose():
    missing=dict(MEASUREMENTS); del missing["title"]
    with pytest.raises(LayoutError,match="E_LAYOUT_MEASUREMENT_REQUIRED"):
        solve_layout(profile(),viewport_inline=1600,viewport_block=900,measurements=missing)
    with pytest.raises(LayoutError,match="E_LAYOUT_CONSTRAINT_CONTRADICTORY"):
        solve_layout(profile(),viewport_inline=300,viewport_block=100,measurements=MEASUREMENTS)


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
        "version": "chrona/layout-profile/v0.7", "id": "optional-source", "writingMode": "horizontal-tb", "requiredThemeTokens": ["spacing.m", "spacing.none"], "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {"rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"}, "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
        "root": {"id": "root", "kind": "column", "inlineSize": "fill", "blockSize": "fill",
                 "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.none"},
                 "alignItems": "stretch", "justifyContent": "start", "children": [
                     {"id": "title", "kind": "slot", "source": "title", "inlineSize": "content", "blockSize": "content",
                      "place": {"inline": "start", "block": "start", "safety": "strict"}, "priority": "required", "overflow": "diagnose"},
                     {"id": "annotations", "kind": "slot", "source": "annotations", "inlineSize": "content", "blockSize": "content",
                      "place": {"inline": "start", "block": "start", "safety": "strict"}, "priority": "optional", "overflow": "diagnose"},
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
      "version":"chrona/layout-profile/v0.7","id":"grid","writingMode":"horizontal-tb","requiredThemeTokens":["spacing.m","spacing.none"],"reviewSurface":{"rowDistribution":"pack","backgroundExtents":{"rowBand":"table","groupBand":"timeline","groupHeaderBand":"both","calendarClosed":"timeline"},"annotationRouting":{"maxBends":4,"maxDetourRatio":2}},
      "root":{"id":"root","kind":"grid","inlineSize":"fill","blockSize":"fill","columnTracks":[{"fr":1},{"fr":1}],"rowTracks":["content"],"gap":{"token":"spacing.m"},"padding":{"token":"spacing.none"},"alignItems":"stretch","justifyContent":"start","children":[
        {"id":"legend","kind":"slot","source":"legend","inlineSize":"fill","blockSize":"content","place":{"inline":"stretch","block":"start","safety":"strict"},"priority":"required","overflow":"diagnose","cell":{"column":1,"row":1}},
        {"id":"notes","kind":"slot","source":"notes","inlineSize":"fill","blockSize":"content","place":{"inline":"stretch","block":"start","safety":"strict"},"priority":"required","overflow":"diagnose","cell":{"column":2,"row":1}}
      ]}}
    theme={"body":{"values":{"spacing.m":{"type":"number","value":16},"spacing.none":{"type":"number","value":0}}}}
    resolved=resolve_layout_profile(raw,available_sources={"legend","notes"},theme=theme)
    result=decisions(solve_layout(resolved,viewport_inline=1000,viewport_block=100,measurements={"legend":MEASUREMENTS["legend"],"notes":MEASUREMENTS["notes"]}))
    assert result["legend"].inline_size == result["notes"].inline_size == Decimal(492)
    assert result["notes"].inline == Decimal(508)


def test_review_surface_requires_the_closed_background_extent_mapping():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    del raw["reviewSurface"]["backgroundExtents"]["rowBand"]
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as error:
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    assert error.value.path == "/reviewSurface/backgroundExtents"


def test_v07_requires_annotation_routing_and_rejects_the_removed_v06_identity():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
    }.items()}
    del raw["reviewSurface"]["annotationRouting"]
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as error:
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    assert error.value.path == "/reviewSurface"

    raw["version"] = "chrona/layout-profile/v0.6"
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as error:
        resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    assert error.value.path == "/version"


def test_annotation_routing_is_manifested_independently_of_relation_routing():
    raw = yaml.safe_load((ROOT / "examples/halcyon-1/layouts/briefing.yaml").read_text(encoding="utf-8"))
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
