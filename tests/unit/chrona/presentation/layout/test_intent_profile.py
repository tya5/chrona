from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import LayoutBase, resolve_layout_profile


ROOT = Path(__file__).parents[5]


def fixture(name):
    return yaml.safe_load((ROOT / "conformance" / name).read_text(encoding="utf-8"))


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
HEADING_SOURCES = SOURCES | {"heading.title", "heading.kicker", "heading.subtitle"}


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


def test_heading_whole_alias_resolves_to_legacy_title_identity():
    legacy = fixture("layout-profile-intent-v0.2.yaml")
    alias = deepcopy(legacy)
    alias["root"]["children"][0]["source"] = "heading"
    legacy_result = resolve_layout_profile(legacy, available_sources=SOURCES, theme=theme())
    alias_result = resolve_layout_profile(alias, available_sources=SOURCES, theme=theme())
    assert alias_result.profile["root"]["children"][0]["source"] == "title"
    assert alias_result.content_hash == legacy_result.content_hash


def test_heading_part_source_is_accepted():
    value = fixture("layout-profile-intent-v0.2.yaml")
    value["root"]["children"][0]["source"] = "heading.subtitle"
    resolved = resolve_layout_profile(value, available_sources=HEADING_SOURCES, theme=theme())
    assert resolved.profile["root"]["children"][0]["source"] == "heading.subtitle"


@pytest.mark.parametrize("first,second", [
    ("heading.title", "heading.title"),
    ("title", "heading.subtitle"),
    ("heading", "heading.kicker"),
    ("heading", "title"),
])
def test_duplicate_heading_claim_fails_at_later_source_pointer(first, second):
    value = fixture("layout-profile-intent-v0.2.yaml")
    value["root"]["children"][0]["source"] = first
    duplicate = deepcopy(value["root"]["children"][0])
    duplicate["id"] = "second-heading"
    duplicate["source"] = second
    value["root"]["children"].insert(1, duplicate)
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as caught:
        resolve_layout_profile(value, available_sources=HEADING_SOURCES, theme=theme())
    assert caught.value.path == "/root/children/1/source"
    assert "heading part" in caught.value.detail
    assert "title" in caught.value.detail or "kicker" in caught.value.detail or "subtitle" in caught.value.detail


def test_heading_claims_are_checked_after_base_overrides_resolve():
    base = fixture("layout-profile-intent-v0.2.yaml")
    base["root"]["children"][0]["source"] = "heading.kicker"
    base["root"]["children"].append({**deepcopy(base["root"]["children"][0]),
                                      "id": "second-kicker", "source": "heading.kicker"})
    identity = "sha256:" + "1" * 64
    derived = {
        "version": base["version"], "id": "derived", "flowDirection": base["flowDirection"],
        "dependencyNetworkFlowDirection": base["dependencyNetworkFlowDirection"],
        "requiredThemeTokens": base["requiredThemeTokens"], "reviewSurface": base["reviewSurface"],
        "extends": {"id": base["id"], "kind": "layout-profile",
                    "store": {"provider": "local", "identity": "test"},
                    "address": "layouts/base.yaml", "revision": {"token": "r1"},
                    "contentIdentity": identity},
        "overrides": {"title": {"inlineSize": {"fixed": 240}}},
    }
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as caught:
        resolve_layout_profile(derived, available_sources=HEADING_SOURCES,
                               theme=theme(), bases={base["id"]: LayoutBase(base, "r1", identity)})
    assert caught.value.path == "/root/children/3/source"


def test_wrong_type_and_missing_tokens_are_rejected():
    value = fixture("layout-profile-intent-v0.2.yaml")
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_REQUIREMENT_TYPE"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme(bad=True))
    value["root"]["children"][2]["itemMinInlineSize"] = {"token": "unknown"}
    with pytest.raises(LayoutError, match="E_LAYOUT_TOKEN_REQUIREMENT_MISSING"):
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
    value["requiredThemeTokens"].append("spacing.s")
    value["requiredThemeTokens"].sort()
    with pytest.raises(LayoutError, match="E_LAYOUT_CONSTRAINT_CONTRADICTORY"):
        resolve_layout_profile(value, available_sources=SOURCES, theme=theme())
