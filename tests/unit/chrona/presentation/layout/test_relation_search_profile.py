"""Declared routing policy normalization, not schema default annotations."""
import json
from copy import deepcopy

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import compose_layout_profile, resolve_layout_profile
from tests.unit.chrona.presentation.layout.test_region_frame_profile import SOURCES, THEME, profile, slot, solved


def _profile(policy=None):
    value = profile(slot("title", "title"))
    if policy is not None:
        value["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2, "search": policy}
    return value


@pytest.mark.parametrize("policy, expected", [(None, "first-fit"), ("first-fit", "first-fit"), ("best", "best")])
def test_policy_reaches_the_manifest_and_canonical_payload(policy, expected):
    manifest = solved(_profile(policy))
    assert manifest.relation_search == expected
    routing = json.loads(manifest.canonical_bytes())["relationRouting"]
    assert routing.get("search", "best") == expected
    if expected == "best":
        assert routing == {"maxBends": 4, "maxDetourRatio": 2.0}


@pytest.mark.parametrize("policy", ["auto", "FIRST-FIT", True, 1, [], {}])
def test_invalid_policy_is_rejected_at_the_schema_boundary(policy):
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(_profile(policy), available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/relationRouting/search")


def test_search_declaration_does_not_remove_required_limits():
    value = _profile()
    value["relationRouting"] = {"search": "best"}
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    assert error.value.diagnostic_id == "E_LAYOUT_SCHEMA"
    assert error.value.path == "/relationRouting"


def test_null_is_not_an_absent_policy():
    value = _profile("best")
    value["relationRouting"]["search"] = None
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/relationRouting/search")


def test_derived_routing_member_is_whole_replacement_not_a_policy_merge():
    base = _profile("best")
    base["relationRouting"]["searchBudget"] = 3
    derived = deepcopy(base)
    derived.pop("root")
    derived.pop("relationRouting")
    derived["id"] = "derived"
    derived["extends"] = {"id": "frames", "kind": "layout-profile",
        "store": {"provider": "local", "identity": "local"}, "address": "layouts/base.yaml",
        "revision": {"token": "v1"}, "contentIdentity": "sha256:" + "0" * 64}
    derived["overrides"] = {"page": {"padding": deepcopy(base["root"]["padding"])}}
    before = deepcopy((base, derived))
    assert solved(compose_layout_profile(derived, base)).relation_search == "best"
    assert solved(compose_layout_profile(derived, base)).relation_search_budget == 3
    assert (base, derived) == before
    derived["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2}
    assert solved(compose_layout_profile(derived, base)).relation_search == "first-fit"
    assert solved(compose_layout_profile(derived, base)).relation_search_budget is None


@pytest.mark.parametrize("policy", ("first-fit", "best"))
def test_explicit_budget_reaches_the_manifest_without_changing_policy(policy):
    value = _profile(policy)
    value["relationRouting"]["searchBudget"] = 7
    manifest = solved(value)
    assert manifest.relation_search_budget == 7
    assert json.loads(manifest.canonical_bytes())["relationRouting"]["searchBudget"] == 7
    assert manifest.relation_search == policy


@pytest.mark.parametrize("budget", (0, -1, True, None, 1.5, "2", []))
def test_invalid_budget_is_rejected_at_the_schema_boundary(budget):
    value = _profile("best")
    value["relationRouting"]["searchBudget"] = budget
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/relationRouting/searchBudget")
