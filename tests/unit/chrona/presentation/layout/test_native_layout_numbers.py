"""Native geometry is authoritative; transport rounding cannot affect it."""
from decimal import Decimal, ROUND_UP, localcontext
import json

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import LayoutError, LayoutManifest, Measurement, Rect, projected_number, source_budget_float
from chrona.presentation.layout.numbers import LayoutNumber, from_source_float
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.tracks import resolve_flexible_tracks


def _relative_grid_profile():
    def slot(node_id, source, row):
        return {"id": node_id, "kind": "slot", "source": source,
                "inlineSize": "fill", "blockSize": {"fixed": 80},
                "cell": {"column": 1, "row": row},
                "place": {"inline": "stretch", "block": "start", "safety": "strict"},
                "priority": "required", "overflow": "visible-overflow"}

    table = slot("table", "table", 1)
    table.pop("cell")
    table_host = {"id": "table-host", "kind": "overlay", "inlineSize": "fill", "blockSize": "fill",
                  "padding": {"inlineStart": 0, "inlineEnd": 0, "blockStart": 3, "blockEnd": 0},
                  "cell": {"column": 1, "row": 3}, "children": [table]}
    timeline = slot("timeline", "timeline", 1)
    timeline.pop("cell")
    timeline_host = {"id": "timeline-host", "kind": "overlay", "inlineSize": "fill", "blockSize": "fill",
                     "padding": 0, "cell": {"column": 1, "row": 2}, "children": [timeline]}

    def grid(node_id, rows, children):
        return {"id": node_id, "kind": "grid", "inlineSize": "fill", "blockSize": "fill",
                "columnTracks": [{"fr": 1}], "rowTracks": [{"fr": weight} for weight in rows],
                "gap": 0, "padding": 0, "alignItems": "stretch", "justifyContent": "start",
                "children": children}

    raw = {
        "version": "chrona/layout-profile/v0.10", "id": "exact-relative-grids",
        "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal",
        "requiredThemeTokens": [],
        "reviewSurface": {"rowDistribution": "pack",
                          "backgroundExtents": {"rowBand": "table", "groupBand": "timeline",
                                                "groupHeaderBand": "both", "calendarClosed": "timeline"},
                          "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
        "root": {"id": "root", "kind": "overlay", "inlineSize": "fill", "blockSize": "fill",
                 "padding": 0, "children": [grid("table-grid", [1, 1, 4], [table_host]),
                                               grid("timeline-grid", [1, 2], [timeline_host])]},
    }
    return resolve_layout_profile(raw, available_sources={"table", "timeline"}, theme={"body": {"values": {}}})


@pytest.mark.parametrize("extent", [600, 10**30, 10**30 + 1000])
def test_equivalent_native_track_origins_keep_the_relative_offset_at_every_extent(extent):
    profile = _relative_grid_profile()
    measurement = Measurement(*(Decimal(80),) * 6)
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_UP
        manifest = solve_layout(profile, viewport_inline=1000, viewport_block=extent,
                                measurements={"table": measurement, "timeline": measurement})
    sources = {item.source: item.bounds for item in manifest.decisions if item.source}
    assert sources["table"].block - sources["timeline"].block == 3
    assert sources["timeline"].block == LayoutNumber(extent, 3)
    assert sources["table"].block_size == sources["timeline"].block_size == 80
    assert profile.distances["/root/children/0/children/0/padding/blockStart"] == Decimal(3)


def test_flexible_tracks_do_not_round_before_the_native_domain_is_entered():
    with localcontext() as context:
        context.prec = 2
        sizes = resolve_flexible_tracks([(Decimal(0), None, Decimal(1))] * 3, Decimal(100))
    assert all(isinstance(size, LayoutNumber) for size in sizes)
    assert sizes == [LayoutNumber(100, 3)] * 3
    assert sum(sizes) == 100


def test_manifest_transport_rounds_once_without_changing_native_geometry():
    bounds = Rect(Decimal("0.125"), Decimal("-0.375"), 10**30, LayoutNumber(1, 3))
    manifest = LayoutManifest("synthetic", "unchanged-identity", "horizontal", "horizontal", bounds, ())
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_UP
        encoded = json.loads(manifest.canonical_bytes(precision=2))
    assert encoded["viewport"] == {"inline": "0.12", "block": "-0.38",
                                   "inlineSize": str(10**30) + ".00", "blockSize": "0.33"}
    assert manifest.viewport.block_size == LayoutNumber(1, 3)
    assert manifest.profile_hash == "unchanged-identity"


def test_invalid_native_input_and_unrepresentable_projection_have_owned_diagnostics():
    with pytest.raises(LayoutError) as caught:
        Rect(Decimal("NaN"), 0, 1, 1)
    assert caught.value.diagnostic_id == "E_LAYOUT_NUMERIC_CONVERSION"
    assert caught.value.path == "/geometry/inline"
    with pytest.raises(LayoutError) as caught:
        projected_number(LayoutNumber(10**10000), path="/timeline/bounds", stage="font-interface")
    assert caught.value.diagnostic_id == "E_LAYOUT_NUMERIC_CONVERSION"
    assert caught.value.path == "/timeline/bounds"
    assert "stage=font-interface" in caught.value.detail


def test_source_library_rounding_cannot_enlarge_the_authoritative_budget():
    budget = LayoutNumber(5, 6)
    assert from_source_float(budget.to_float()) > budget
    assert from_source_float(source_budget_float(budget, path="/table/inlineSize")) <= budget
    assert source_budget_float(LayoutNumber(1, 10), path="/title/inlineSize") == 0.1
