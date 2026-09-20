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
    value = yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text())
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


def test_grid_and_distribution_are_deterministic():
    raw={
      "version":"chrona/layout-profile/v0.2","id":"grid","writingMode":"horizontal-tb",
      "root":{"id":"root","kind":"grid","inlineSize":"fill","blockSize":"fill","columnTracks":[{"fr":1},{"fr":1}],"rowTracks":["content"],"gap":{"token":"spacing.m"},"padding":{"token":"spacing.none"},"alignItems":"stretch","justifyContent":"start","children":[
        {"id":"legend","kind":"slot","source":"legend","inlineSize":"fill","blockSize":"content","place":{"inline":"stretch","block":"start","safety":"strict"},"priority":"required","overflow":"diagnose","cell":{"column":1,"row":1}},
        {"id":"notes","kind":"slot","source":"notes","inlineSize":"fill","blockSize":"content","place":{"inline":"stretch","block":"start","safety":"strict"},"priority":"required","overflow":"diagnose","cell":{"column":2,"row":1}}
      ]}}
    theme={"body":{"values":{"spacing.m":{"type":"number","value":16},"spacing.none":{"type":"number","value":0}}}}
    resolved=resolve_layout_profile(raw,available_sources={"legend","notes"},theme=theme)
    result=decisions(solve_layout(resolved,viewport_inline=1000,viewport_block=100,measurements={"legend":MEASUREMENTS["legend"],"notes":MEASUREMENTS["notes"]}))
    assert result["legend"].inline_size == result["notes"].inline_size == Decimal(492)
    assert result["notes"].inline == Decimal(508)


def relative_profile():
    raw = yaml.safe_load((ROOT / "conformance/layout-profile-relative-v0.2.yaml").read_text())
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
