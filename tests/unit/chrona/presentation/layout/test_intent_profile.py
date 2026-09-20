from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import LayoutBase, resolve_layout_profile


ROOT = Path(__file__).parents[5]


def fixture(name):
    return yaml.safe_load((ROOT / "conformance" / name).read_text())


def theme(*, bad=False):
    values = {
        "spacing.none": {"type": "number", "value": 0},
        "spacing.s": {"type": "number", "value": 8},
        "spacing.m": {"type": "number", "value": 16},
        "spacing.l": {"type": "number", "value": 24},
        "panel.minimum": {"type": "color" if bad else "number", "value": "#fff" if bad else 240},
    }
    return {"body": {"values": values}}


SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes", "group-details", "observations", "milestones"}


def test_complete_profile_resolves_tokens_and_canonical_hash():
    value = fixture("layout-profile-intent-v0.2.yaml")
    first = resolve_layout_profile(value, available_sources=SOURCES, theme=theme())
    second = resolve_layout_profile(deepcopy(value), available_sources=SOURCES, theme=theme())
    assert first.content_hash == second.content_hash
    assert first.distances["/root/gap"] == 16
    assert not first.literal_distance_paths


def test_stable_id_override_changes_only_named_nodes():
    base = fixture("layout-profile-intent-v0.2.yaml")
    override = fixture("layout-profile-override-v0.2.yaml")
    resolved = resolve_layout_profile(
        override, available_sources=SOURCES, theme=theme(),
        bases={"executive-review": LayoutBase(base, "snapshot-42", override["extends"]["contentIdentity"])},
    )
    assert resolved.profile["root"]["gap"] == {"token": "spacing.s"}
    review = resolved.profile["root"]["children"][1]
    assert review["id"] == "review" and review["gap"] == {"token": "spacing.l"}


@pytest.mark.parametrize("mutate,diagnostic", [
    (lambda value: value["root"]["children"].append(deepcopy(value["root"]["children"][0])), "E_LAYOUT_NODE_DUPLICATE"),
    (lambda value: value["root"]["children"][0].update(source="summary"), "E_LAYOUT_SOURCE_UNAVAILABLE"),
])
def test_semantic_failures_have_stable_ids(mutate, diagnostic):
    value = fixture("layout-profile-intent-v0.2.yaml"); mutate(value)
    with pytest.raises(LayoutError, match=diagnostic):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())


def test_wrong_type_and_missing_tokens_are_rejected():
    value = fixture("layout-profile-intent-v0.2.yaml")
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_TYPE"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme(bad=True))
    value["root"]["children"][2]["itemMinInlineSize"] = {"token": "unknown"}
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_UNKNOWN"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())


def test_superseded_single_target_anchor_is_structurally_rejected():
    value = fixture("layout-profile-intent-v0.2.yaml")
    value["root"]["children"][0]["anchor"] = {
        "self": {"inline": "center", "block": "center"},
        "target": {"ref": "parent", "inline": "center", "block": "center"},
        "gap": {"token": "spacing.s"},
    }
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())


def test_unknown_override_and_base_cycle_are_rejected():
    base = fixture("layout-profile-intent-v0.2.yaml")
    override = fixture("layout-profile-override-v0.2.yaml")
    identity = override["extends"]["contentIdentity"]
    override["overrides"] = {"missing": {"gap": {"token": "spacing.s"}}}
    with pytest.raises(LayoutError, match="E_LAYOUT_OVERRIDE_UNKNOWN"):
        resolve_layout_profile(override, available_sources=SOURCES, theme=theme(), bases={"executive-review": LayoutBase(base, "snapshot-42", identity)})

    cyclic = deepcopy(override); cyclic["id"] = "executive-review"; cyclic["extends"]["id"] = "executive-review"
    with pytest.raises(LayoutError, match="E_LAYOUT_BASE_CYCLE"):
        resolve_layout_profile(cyclic, available_sources=SOURCES, theme=theme(), bases={"executive-review": LayoutBase(cyclic, "snapshot-42", identity)})


def test_relative_references_enforce_axis_scope_and_cycles():
    value = fixture("layout-profile-relative-v0.2.yaml")
    value["root"]["children"][2]["anchor"]["target"]["block"] = {
        "ref": "barrier:label-end", "point": "end",
    }
    with pytest.raises(LayoutError, match="E_LAYOUT_REFERENCE_SCOPE"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())

    value = fixture("layout-profile-relative-v0.2.yaml")
    value["root"]["barriers"]["label-end"]["members"] = ["milestones"]
    with pytest.raises(LayoutError, match="E_LAYOUT_CONSTRAINT_CYCLE"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())


def test_center_to_center_axis_gap_is_rejected():
    value = fixture("layout-profile-relative-v0.2.yaml")
    anchor = value["root"]["children"][2]["anchor"]
    anchor["self"]["block"] = "center"
    anchor["target"]["block"] = {"ref": "parent", "point": "center"}
    anchor["gap"]["block"] = {"token": "spacing.s"}
    with pytest.raises(LayoutError, match="E_LAYOUT_CONSTRAINT_CONTRADICTORY"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())
