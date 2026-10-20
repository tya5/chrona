"""The global relation drawing style is declared by Layout Profile (#1047)."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import (
    LayoutError, LayoutManifest, Rect, RelationRouteStyle,
)
from chrona.presentation.layout.profile import resolve_layout_profile

from tests.unit.chrona.presentation.layout.test_relation_entry_profile import (
    SOURCES, THEME, solved, with_routing,
)


@pytest.mark.parametrize(("routing", "expected"), [
    (None, RelationRouteStyle.ORTHOGONAL),
    ({"maxBends": 4, "maxDetourRatio": 2}, RelationRouteStyle.ORTHOGONAL),
    ({"maxBends": 4, "maxDetourRatio": 2, "style": "orthogonal"}, RelationRouteStyle.ORTHOGONAL),
    ({"maxBends": 4, "maxDetourRatio": 2, "style": "curved"}, RelationRouteStyle.CURVED),
])
def test_profile_style_reaches_layout_manifest(routing, expected):
    assert solved(with_routing(routing)).relation_style is expected


def test_omitted_and_explicit_orthogonal_keep_the_same_routing_payload():
    omitted = json.loads(solved(with_routing(None)).canonical_bytes())
    explicit = json.loads(solved(with_routing(
        {"maxBends": 4, "maxDetourRatio": 2, "style": "orthogonal"}
    )).canonical_bytes())

    # The source profile hashes differ, but no new default style is added to the
    # canonical routing manifest and all other solved layout payload is stable.
    omitted.pop("profileHash")
    explicit.pop("profileHash")
    assert omitted == explicit
    assert "style" not in omitted["relationRouting"]
    assert "style" not in explicit["relationRouting"]


def test_curved_style_is_recorded_only_when_nondefault():
    payload = json.loads(solved(with_routing(
        {"maxBends": 4, "maxDetourRatio": 2, "style": "curved"}
    )).canonical_bytes())

    assert payload["relationRouting"]["style"] == "curved"


@pytest.mark.parametrize("style", ["bezier", "ORTHOGONAL", 1, None, True])
def test_unknown_profile_style_fails_at_its_exact_pointer(style):
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(
            with_routing({"maxBends": 4, "maxDetourRatio": 2, "style": style}),
            available_sources=SOURCES, theme=THEME,
        )

    assert (error.value.diagnostic_id, error.value.path) == (
        "E_LAYOUT_SCHEMA", "/relationRouting/style"
    )


def test_layout_manifest_direct_construction_validates_the_closed_style_enum():
    base = dict(
        profile_id="test", profile_hash="sha256:test", flow_direction="horizontal",
        dependency_network_flow_direction="horizontal",
        viewport=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(100)), decisions=(),
    )

    assert LayoutManifest(**base).relation_style is RelationRouteStyle.ORTHOGONAL
    assert LayoutManifest(**base, relation_style="curved").relation_style is RelationRouteStyle.CURVED
    with pytest.raises(ValueError, match="E_LAYOUT_RELATION_STYLE_INVALID"):
        LayoutManifest(**base, relation_style="bezier")
