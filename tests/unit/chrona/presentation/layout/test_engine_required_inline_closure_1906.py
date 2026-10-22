from decimal import Decimal
from pathlib import Path

import yaml
import pytest

from chrona.presentation.layout.engine import (
    LayoutSizingContext,
    measure_required_normal_flow_inline,
    solve_layout,
    _measure_node,
)
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.profile import resolve_layout_profile


ROOT = Path(__file__).parents[5]
SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}
MEASUREMENTS = {
    "title": Measurement(Decimal(150), Decimal(300), Decimal(600), Decimal(20), Decimal(40), Decimal(80)),
    "table": Measurement(Decimal(150), Decimal(300), Decimal(600), Decimal(300), Decimal(600), Decimal(1200)),
    "timeline-axis": Measurement(Decimal(250), Decimal(500), Decimal(1000), Decimal(25), Decimal(50), Decimal(100)),
    "timeline": Measurement(Decimal(250), Decimal(500), Decimal(1000), Decimal(300), Decimal(600), Decimal(1200)),
    "legend": Measurement(Decimal(120), Decimal(240), Decimal(480), Decimal(16), Decimal(32), Decimal(64),
                           Decimal(24), Decimal(24)),
    "notes": Measurement(Decimal(150), Decimal(300), Decimal(600), Decimal(16), Decimal(32), Decimal(64),
                         Decimal(20), Decimal(20)),
}


def resolved_profile(*, row_inline=None):
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))
    if row_inline is not None:
        raw["root"]["children"][1]["inlineSize"] = row_inline
    values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24,
        "panel.minimum": 180,
    }.items()}
    return resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})


def test_fill_root_closes_admitted_required_owner_minimum_through_normal_flow():
    profile = resolved_profile()
    baseline = measure_required_normal_flow_inline(profile, MEASUREMENTS)
    required = Decimal("1400")
    closed = measure_required_normal_flow_inline(profile, MEASUREMENTS, {"review": required})
    # The row's outer floor flows through the page column; the root's own 24px
    # padding remains normal engine-owned ancestry, not part of the owner floor.
    assert closed == required + Decimal(48)
    assert closed > baseline


def test_owner_floor_does_not_inflate_descendant_source_minima_and_context_is_immutable():
    profile = resolved_profile()
    supplied = {"review": Decimal("1400")}
    context = LayoutSizingContext({}, owner_inline_minima=supplied)
    supplied["review"] = Decimal("1800")
    assert context.owner_inline_minima["review"] == Decimal("1400")
    with pytest.raises(TypeError):
        context.owner_inline_minima["review"] = Decimal("2000")

    root = profile.profile["root"]
    row = root["children"][1]
    raw_children = row["children"]
    table = _measure_node(raw_children[0], "/root/children/1/children/0", MEASUREMENTS, profile,
                          owner_inline_minima=context.owner_inline_minima)
    timeline = _measure_node(raw_children[1], "/root/children/1/children/1", MEASUREMENTS, profile,
                             owner_inline_minima=context.owner_inline_minima)
    assert table.min_inline == MEASUREMENTS["table"].min_inline
    assert timeline.min_inline == max(MEASUREMENTS["timeline-axis"].min_inline,
                                      MEASUREMENTS["timeline"].min_inline)


def test_fixed_and_fixed_max_owner_tracks_remain_authoritative_under_floor():
    for spec in ({"fixed": 600}, {"minmax": {"min": {"fixed": 300}, "max": {"fixed": 600}}}):
        profile = resolved_profile(row_inline=spec)
        manifest = solve_layout(
            profile,
            viewport_inline=1600,
            viewport_block=900,
            measurements=MEASUREMENTS,
            sizing=LayoutSizingContext({}, owner_inline_minima={"review": Decimal("1400")}),
        )
        review = next(item for item in manifest.decisions if item.node_id == "review")
        assert review.bounds.inline_size == Decimal(600)


def test_empty_owner_minima_preserve_layout_bytes():
    profile = resolved_profile()
    ordinary = solve_layout(profile, viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS)
    explicit_empty = solve_layout(
        profile, viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS,
        sizing=LayoutSizingContext({}, owner_inline_minima={}),
    )
    assert explicit_empty.canonical_bytes() == ordinary.canonical_bytes()


def test_required_inline_closure_excludes_anchored_overlay_children():
    raw = yaml.safe_load((ROOT / "tests/fixtures/layout-profiles/overlay-briefing.yaml").read_text(encoding="utf-8"))
    values = {name: {"type": "number", "value": value} for name, value in {
        "panel.review.block": 700, "panel.side": 240, "spacing.l": 24,
        "spacing.m": 16, "spacing.none": 0,
    }.items()}
    profile = resolve_layout_profile(raw, available_sources=SOURCES, theme={"body": {"values": values}})
    measurements = {name: MEASUREMENTS[name] for name in SOURCES}
    baseline = measure_required_normal_flow_inline(profile, measurements)
    with_anchored_floor = measure_required_normal_flow_inline(
        profile, measurements, {"sidebar": Decimal("5000")})
    assert with_anchored_floor == baseline
