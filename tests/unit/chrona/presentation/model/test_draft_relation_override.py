"""The Draft override preserves declarations and freezes effective identity."""
from copy import deepcopy

import pytest

from chrona.core.identity import content_identity
from chrona.presentation.contracts import ClosureIdentity, PresentationResourceSource
from chrona.presentation.model.closure import _draft_relation_override


@pytest.mark.parametrize("declaration", ["semantic", {"mode": "semantic", "labels": "none"}])
def test_override_changes_only_mode_without_mutating_authored_input(declaration):
    value = {"body": {"visibility": {"relations": declaration, "labels": True}, "selection": "all"}}
    original = deepcopy(value)
    source = PresentationResourceSource(ClosureIdentity("view", "v", "draft", "sha256:authored"), value)
    effective = _draft_relation_override(source, "none")
    assert value == original
    expected = deepcopy(value)
    expected["body"]["visibility"]["relations"] = (
        dict(declaration, mode="none") if isinstance(declaration, dict) else "none")
    assert effective.value == expected
    assert effective.identity.content_identity == content_identity(expected)
    assert effective.identity.id == source.identity.id
    assert effective.identity.revision == "draft"
    assert _draft_relation_override(source, "semantic") is source


@pytest.mark.parametrize("value", [{"body": []}, {"body": {"visibility": []}}])
def test_malformed_container_remains_for_normal_ingress_validation(value):
    source = PresentationResourceSource(ClosureIdentity("view", "v", "draft", "sha256:authored"), value)
    assert _draft_relation_override(source, "none") is source
