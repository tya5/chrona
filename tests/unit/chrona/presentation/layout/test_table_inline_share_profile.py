"""Admission only; allocation and materializer acceptance are separate gates."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import LayoutBase, resolve_layout_profile
from chrona.resources import schema_validator
from tests.unit.chrona.presentation.layout.test_intent_profile import SOURCES, fixture, theme


def _profile():
    return fixture("layout-profile-intent-v0.2.yaml")


def _table(value):
    return value["root"]["children"][1]["children"][0]


def _resolve(value, **kwargs):
    return resolve_layout_profile(value, available_sources=SOURCES, theme=theme(), **kwargs)


@pytest.mark.parametrize("share", [0.01, 0.4, 1])
def test_valid_share_is_retained_without_mutating_authored_input(share):
    value = _profile()
    _table(value)["maxInlineShare"] = share
    original = deepcopy(value)
    assert schema_validator("layout-profile-v0.10.schema.yaml").is_valid(value)
    assert _table(_resolve(value).profile)["maxInlineShare"] == share
    assert value == original


@pytest.mark.parametrize("share", [0, -1, 1.01, True, None, "0.4", {}, float("inf"),
                                  float("-inf"), float("nan")])
def test_invalid_share_fails_at_exact_declaration_pointer(share):
    value = _profile()
    _table(value)["maxInlineShare"] = share
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as caught:
        _resolve(value)
    assert caught.value.path == "/root/children/1/children/0/maxInlineShare"


@pytest.mark.parametrize("source", ["title", "legend", "timeline", "notes"])
def test_share_is_not_admitted_on_another_source(source):
    value = _profile()
    _table(value).update(source=source, maxInlineShare=0.4)
    assert not schema_validator("layout-profile-v0.10.schema.yaml").is_valid(value)
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        _resolve(value)


def test_share_is_not_admitted_on_a_container():
    value = _profile()
    value["root"]["children"][1]["maxInlineShare"] = 0.4
    assert not schema_validator("layout-profile-v0.10.schema.yaml").is_valid(value)
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA") as caught:
        _resolve(value)
    assert caught.value.path == "/root/children/1/maxInlineShare"


def test_absence_preserves_complete_profile_and_canonical_identity():
    value = _profile()
    expected = "sha256:" + sha256(json.dumps(value, ensure_ascii=False,
        separators=(",", ":"), sort_keys=True).encode()).hexdigest()
    resolved = _resolve(value)
    assert resolved.profile == value
    assert resolved.content_hash == expected
    assert "maxInlineShare" not in _table(resolved.profile)


@pytest.mark.parametrize("node_id,valid", [("table", True), ("title", False), ("review", False)])
def test_override_is_checked_against_the_resolved_target(node_id, valid):
    base = _profile()
    value = fixture("layout-profile-override-v0.2.yaml")
    value["overrides"] = {node_id: {"maxInlineShare": 0.4}}
    value["requiredThemeTokens"] = base["requiredThemeTokens"]
    bases = {base["id"]: LayoutBase(base, "snapshot-42", value["extends"]["contentIdentity"])}
    if valid:
        assert _table(_resolve(value, bases=bases).profile)["maxInlineShare"] == 0.4
    else:
        with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
            _resolve(value, bases=bases)
