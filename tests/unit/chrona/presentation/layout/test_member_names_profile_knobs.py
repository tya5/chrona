"""Layout Profile ``reviewSurface.memberNames`` knobs (#573, I573-1): schema, carriage, wiring."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.labels import LabelRequest, LabelRect, CollisionDomain
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import LayoutBase, resolve_layout_profile
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.surface_member_labels import _member_full_band, _member_reach


ROOT = Path(__file__).parents[5]
SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}
THEME = {"body": {"values": {name: {"type": "number", "value": value} for name, value in {
    "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
}.items()}}}


def _m(inline, block, *, baseline=None):
    value = None if baseline is None else Decimal(baseline)
    return Measurement(Decimal(inline) / 2, Decimal(inline), Decimal(inline) * 2, Decimal(block) / 2, Decimal(block),
                       Decimal(block) * 2, value, value)


MEASUREMENTS = {"title": _m(300, 40), "table": _m(300, 600), "timeline-axis": _m(500, 50),
                "timeline": _m(500, 600), "legend": _m(240, 32, baseline=24), "notes": _m(300, 32, baseline=20)}


def fixture(name):
    return yaml.safe_load((ROOT / "conformance" / name).read_text(encoding="utf-8"))


def resolve(value, **kwargs):
    return resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, **kwargs)


def request(lane_row_id):
    return LabelRequest("member-label:x", "x", "X", LabelRect(0, 0, 10, 10), ("end",), "text", "plot-label",
                        CollisionDomain("timeline", "overlay"), "suppress", semantic_id="memberLabel",
                        lane_row_id=lane_row_id)


class Manifest:
    def __init__(self, row_distribution, member_names):
        self.row_distribution = row_distribution
        self.member_names = member_names


@pytest.mark.parametrize("member_names", [
    {"maxEndGapEm": 3.5}, {"search": "side-band"}, {"maxEndGapEm": 0, "search": "full-band"}, {},
])
def test_member_names_are_accepted_and_kept_in_the_resolved_profile(member_names):
    value = fixture("layout-profile-intent-v0.2.yaml")
    value["reviewSurface"]["memberNames"] = member_names
    assert resolve(value).profile["reviewSurface"]["memberNames"] == member_names


@pytest.mark.parametrize("member_names", [
    {"unknown": 1}, {"maxEndGapEm": -0.1}, {"maxEndGapEm": 100.5}, {"maxEndGapEm": "2"},
    {"maxEndGapEm": True}, {"search": "band"}, {"search": None},
])
def test_member_names_reject_unknown_keys_and_bad_values(member_names):
    value = fixture("layout-profile-intent-v0.2.yaml")
    value["reviewSurface"]["memberNames"] = member_names
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        resolve(value)


def test_member_names_do_not_widen_the_closed_review_surface():
    value = fixture("layout-profile-intent-v0.2.yaml")
    value["reviewSurface"]["memberLabels"] = {}
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        resolve(value)


def test_derived_profile_carries_only_the_member_names_it_declares():
    base = fixture("layout-profile-intent-v0.2.yaml")
    base["reviewSurface"]["memberNames"] = {"maxEndGapEm": 5}
    override = fixture("layout-profile-override-v0.2.yaml")
    identity = override["extends"]["contentIdentity"]
    bases = {"executive-review": LayoutBase(base, "snapshot-42", identity)}

    omitted = resolve(deepcopy(override), bases=bases)
    assert "memberNames" not in omitted.profile["reviewSurface"]

    declared = deepcopy(override)
    declared["reviewSurface"]["memberNames"] = {"maxEndGapEm": 3, "search": "full-band"}
    carried = resolve(declared, bases=bases)
    assert carried.profile["reviewSurface"]["memberNames"] == {"maxEndGapEm": 3, "search": "full-band"}


def test_member_names_reach_the_manifest_and_absent_leaves_its_bytes_unchanged():
    measurements = MEASUREMENTS

    def manifest(member_names):
        value = fixture("layout-profile-intent-v0.2.yaml")
        if member_names is not None:
            value["reviewSurface"]["memberNames"] = member_names
        return solve_layout(resolve(value), viewport_inline=1600, viewport_block=900, measurements=measurements)

    absent = manifest(None)
    assert absent.member_names == {}
    assert b"memberNames" not in absent.canonical_bytes()
    assert b"memberNames" not in manifest({}).canonical_bytes()
    declared = manifest({"maxEndGapEm": 4})
    assert declared.member_names == {"maxEndGapEm": 4}
    assert b'"memberNames":{"maxEndGapEm":4}' in declared.canonical_bytes()


@pytest.mark.parametrize("member_names,expected", [({}, 40.0), ({"maxEndGapEm": 2}, 40.0),
                                                   ({"maxEndGapEm": 0.5}, 10.0), ({"maxEndGapEm": 4}, 80.0),
                                                   ({"maxEndGapEm": 0}, 0.0)])
def test_reach_is_declared_em_times_font_size_and_defaults_to_two(member_names, expected):
    assert _member_reach(20.0, member_names) == expected


@pytest.mark.parametrize("distribution,lane,search,expected", [
    ("fill", "row", None, True), ("pack", "row", None, False), ("fill", None, None, False), ("pack", None, None, False),
    ("fill", "row", "side-band", False), ("pack", "row", "full-band", True),
    ("fill", None, "full-band", True), ("pack", None, "side-band", False),
])
def test_search_defaults_to_the_lane_fill_coupling_and_a_declared_value_replaces_it(distribution, lane, search, expected):
    names = {} if search is None else {"search": search}
    assert _member_full_band(request(lane), Manifest(distribution, names)) is expected
