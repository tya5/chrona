"""#1214: the least fitting block extent when the block extent feeds an aspect-ratio flow's inline extent.

The fit predicate "the required slot is allocated its demand" is monotone while block extent cannot change inline
demand. An inline `aspectRatio` couples them, so the first fitting integral extent must be searched, not bisected.
Fixtures are synthetic (the profile and measurements are in this file); nothing reads `examples/`.
"""
from decimal import Decimal

from chrona.presentation.layout.engine import (_block_extent_feeds_inline, _first_fitting_extent,
                                               resolve_content_block_extent, solve_layout)
from chrona.presentation.layout.model import Measurement
from chrona.presentation.layout.profile import resolve_layout_profile

SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}


def m(i, b):
    return Measurement(Decimal(i) / 2, Decimal(i), Decimal(i) * 2, Decimal(b) / 2, Decimal(b), Decimal(b) * 2, None, None)


def _flow_profile(slot_sources, *, flow_inline=None, flow_block="fill"):
    children = [
        {"id": f"source-{index}", "kind": "slot", "source": source,
         "inlineSize": "content", "blockSize": "fill",
         "place": {"inline": "start", "block": "stretch" if source == "timeline" else "start", "safety": "strict"},
         "priority": "required", "overflow": "visible-overflow"}
        for index, source in enumerate(slot_sources)
    ]
    root = {
        "id": "root", "kind": "overlay", "inlineSize": "fill", "blockSize": "fill",
        "padding": {"token": "spacing.none"},
        "children": [{
            "id": "flow", "kind": "flow", "inlineSize": flow_inline or {"aspectRatio": 1},
            "blockSize": flow_block, "itemMinInlineSize": 1,
            "gap": {"token": "spacing.none"}, "padding": {"token": "spacing.none"},
            "alignItems": "start", "justifyContent": "start", "children": children,
        }],
    }
    raw = {
        "version": "chrona/layout-profile/v0.10", "id": "coupled-aspect-flow",
        "flowDirection": "horizontal", "dependencyNetworkFlowDirection": "horizontal",
        "requiredThemeTokens": ["spacing.none"],
        "reviewSurface": {
            "rowDistribution": "pack",
            "backgroundExtents": {"rowBand": "table", "groupBand": "timeline",
                                  "groupHeaderBand": "both", "calendarClosed": "timeline"},
            "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2},
        },
        "root": root,
    }
    return resolve_layout_profile(raw, available_sources=SOURCES,
                                  theme={"body": {"values": {"spacing.none": {"type": "number", "value": 0}}}})


def _blocks(manifest):
    return {item.source: item.bounds.block_size for item in manifest.decisions if item.source}


TWO = {"source-0": m(100, 20), "source-1": m(100, 100)}
FOUR = {"source-0": m(100, 20), "source-1": m(100, 20), "source-2": m(100, 100), "source-3": m(100, 20)}


def test_the_first_extent_that_stretches_the_required_slot_is_selected_with_native_verification():
    content_sized = False
    profile = _flow_profile(("timeline", "notes"))
    probe = [solve_layout(profile, viewport_inline=400, viewport_block=extent, measurements=TWO,
                          content_sized=content_sized) for extent in (100, 199, 200)]
    assert [_blocks(item)["timeline"] for item in probe] == [Decimal(20), Decimal(20), Decimal(100)]

    resolution = resolve_content_block_extent(
        profile, viewport_inline=400, minimum_block=100, measurements=TWO,
        required_blocks={"timeline": Decimal(80)}, content_sized=content_sized)

    assert resolution.extent == 200 and not resolution.short_sources
    final = solve_layout(profile, viewport_inline=400, viewport_block=resolution.extent, measurements=TWO,
                         content_sized=content_sized)
    assert _blocks(final)["timeline"] >= Decimal(80)


def test_a_non_monotone_fit_predicate_does_not_let_a_global_bisection_skip_an_earlier_branch():
    profile = _flow_profile(("table", "legend", "notes", "timeline"))
    allocated = {extent: _blocks(solve_layout(profile, viewport_inline=400, viewport_block=extent,
                                              measurements=FOUR))["timeline"] for extent in (200, 300, 400)}
    assert allocated == {200: Decimal(100), 300: Decimal(20), 400: Decimal(100)}

    resolution = resolve_content_block_extent(
        profile, viewport_inline=400, minimum_block=100, measurements=FOUR,
        required_blocks={"timeline": Decimal(80)})

    assert resolution.extent == 200


def test_the_requested_minimum_is_kept_when_it_already_fits():
    profile = _flow_profile(("timeline", "notes"))

    resolution = resolve_content_block_extent(
        profile, viewport_inline=400, minimum_block=250, measurements=TWO, required_blocks={"timeline": Decimal(80)})

    assert resolution.extent == 250


def test_a_requirement_no_extent_can_meet_keeps_the_requested_finite_fallback_with_its_shortage():
    profile = _flow_profile(("timeline", "notes"), flow_inline={"fixed": 100}, flow_block={"fixed": 50})

    resolution = resolve_content_block_extent(
        profile, viewport_inline=400, minimum_block=100, measurements=TWO, required_blocks={"timeline": Decimal(80)})

    assert resolution.extent == 100
    assert [(item.source_id, item.required_block) for item in resolution.short_sources] == [("timeline", Decimal(80))]


def test_the_coupling_is_detected_only_for_an_inline_aspect_ratio():
    assert _block_extent_feeds_inline(_flow_profile(("timeline", "notes")))
    assert not _block_extent_feeds_inline(_flow_profile(("timeline", "notes"), flow_inline="fill"))


def test_the_scan_returns_the_least_fitting_extent_for_a_non_monotone_predicate_and_the_known_fit_otherwise():
    islands = {200, 201, 400}

    assert _first_fitting_extent(lambda extent: extent in islands, 100, 400) == 200
    assert _first_fitting_extent(lambda extent: extent >= 300, 100, 400) == 300
    assert _first_fitting_extent(lambda extent: False, 100, 240) == 240  # the verified fit bounds the scan
    assert _first_fitting_extent(lambda extent: True, 150, 240) == 150  # never below the requested minimum
