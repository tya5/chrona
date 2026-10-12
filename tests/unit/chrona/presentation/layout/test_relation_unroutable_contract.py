"""Staged #1427 schema/typed admission; recovery/default flip is not implemented here."""
from decimal import Decimal
import json

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import LayoutError, Measurement, RelationUnroutableMode
from chrona.presentation.layout.profile import resolve_layout_profile


def _profile(mode=None):
    value = {
        "version": "chrona/layout-profile/v0.10", "id": "resolution-contract",
        "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal",
        "requiredThemeTokens": [],
        "reviewSurface": {
            "rowDistribution": "pack",
            "backgroundExtents": {"rowBand": "table", "groupBand": "timeline",
                                  "groupHeaderBand": "both", "calendarClosed": "timeline"},
            "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2},
        },
        "root": {"id": "root", "kind": "overlay", "inlineSize": "fill",
                 "blockSize": "fill", "padding": 0, "children": [
                     {"id": "plot", "kind": "slot", "source": "timeline",
                      "inlineSize": "fill", "blockSize": "fill",
                      "place": {"inline": "start", "block": "start", "safety": "safe"},
                      "priority": "required", "overflow": "visible-overflow"},
                 ]},
    }
    if mode is not None:
        value["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2,
                                    "unroutable": mode}
    return value


def _resolve(value):
    return resolve_layout_profile(value, available_sources={"timeline"},
                                  theme={"body": {"values": {}}})


def _manifest(value):
    measurement = Measurement(*(Decimal(n) for n in (1, 10, 1000, 1, 10, 1000)))
    return solve_layout(_resolve(value), viewport_inline=300, viewport_block=200,
                        measurements={"plot": measurement})


@pytest.mark.parametrize("mode", tuple(RelationUnroutableMode))
def test_declared_mode_is_admitted_and_closed_as_a_typed_layout_value(mode):
    manifest = _manifest(_profile(mode.value))
    assert manifest.relation_unroutable is mode
    canonical = json.loads(manifest.canonical_bytes())["relationRouting"]
    assert canonical.get("unroutable", "suppress") == mode.value


@pytest.mark.parametrize("mode", ("", "ignore", False, 1, []))
def test_invalid_resolution_modes_are_rejected_before_geometry(mode):
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        _resolve(_profile(mode))


def test_omitted_mode_closes_as_relax_after_the_atomic_default_flip():
    manifest = _manifest(_profile())
    assert manifest.relation_unroutable is RelationUnroutableMode.RELAX
    assert json.loads(manifest.canonical_bytes())["relationRouting"]["unroutable"] == "relax"
