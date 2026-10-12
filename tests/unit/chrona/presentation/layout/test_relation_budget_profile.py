"""Declared additional budget, without a routing-policy switch."""
import json
from copy import deepcopy

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import compose_layout_profile, resolve_layout_profile
from tests.unit.chrona.presentation.layout.test_region_frame_profile import SOURCES, THEME, profile, slot, solved


def _profile(budget=None):
    value = profile(slot("title", "title"))
    if budget is not None:
        value["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2, "searchBudget": budget}
    return value


def test_omitted_budget_preserves_manifest_bytes():
    manifest = solved(_profile())
    assert manifest.relation_search_budget is None
    assert json.loads(manifest.canonical_bytes())["relationRouting"] == {
        "maxBends": 4, "maxDetourRatio": 2.0}


def test_explicit_budget_reaches_manifest():
    manifest = solved(_profile(7))
    assert manifest.relation_search_budget == 7
    assert json.loads(manifest.canonical_bytes())["relationRouting"]["searchBudget"] == 7


@pytest.mark.parametrize("budget", (0, -1, True, None, 1.5, "2", []))
def test_invalid_budget_is_rejected_at_schema_boundary(budget):
    value = _profile(7)
    value["relationRouting"]["searchBudget"] = budget
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/relationRouting/searchBudget")


def test_budget_does_not_remove_required_limits():
    value = _profile()
    value["relationRouting"] = {"searchBudget": 7}
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/relationRouting")


def test_removed_search_member_is_not_a_hidden_compatibility_path():
    value = _profile()
    value["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2, "search": "best"}
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    assert error.value.diagnostic_id == "E_LAYOUT_SCHEMA"


def test_derived_routing_member_is_whole_replacement_not_budget_merge():
    base = _profile(3)
    derived = deepcopy(base)
    derived.pop("root")
    derived.pop("relationRouting")
    derived["id"] = "derived"
    derived["extends"] = {"id": "frames", "kind": "layout-profile",
        "store": {"provider": "local", "identity": "local"}, "address": "layouts/base.yaml",
        "revision": {"token": "v1"}, "contentIdentity": "sha256:" + "0" * 64}
    derived["overrides"] = {"page": {"padding": deepcopy(base["root"]["padding"])}}
    before = deepcopy((base, derived))
    assert solved(compose_layout_profile(derived, base)).relation_search_budget == 3
    assert (base, derived) == before
    derived["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2}
    assert solved(compose_layout_profile(derived, base)).relation_search_budget is None
