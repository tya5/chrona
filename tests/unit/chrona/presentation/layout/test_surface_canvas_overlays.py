from copy import deepcopy
from decimal import Decimal
from dataclasses import replace

from chrona.presentation.layout.dependency_network import compose_dependency_network_layout
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request
from tests.unit.chrona.presentation.scene.test_v05_builder import _theme
from tests.unit.chrona.presentation.layout.test_dependency_network import _measured, _network


GRAIN = {
    "kind": "seeded", "algorithm": "splitmix64-v1", "motif": "grain",
    "seed": 7, "tile": {"inlineSize": 12, "blockSize": 10}, "count": 2, "radius": 1,
}


def _theme_with_overlays(*, pattern=True, radial=True):
    themed = deepcopy(_theme())
    roles, values = themed["body"]["roles"], themed["body"]["values"]
    if pattern:
        values["overlay-grain"] = {"type": "pattern", "value": GRAIN}
        roles["canvas-overlay"] = {"pattern": "overlay-grain"}
    if radial:
        radial_values = {
            "radialCenterInline": Decimal("0.5"), "radialCenterBlock": Decimal("0.5"),
            "radialRadiusInline": Decimal("0.75"), "radialRadiusBlock": Decimal("0.75"),
            "radialInnerStop": Decimal(0),
        }
        roles["canvas-overlay-gradient"] = {}
        for name, value in radial_values.items():
            token = f"overlay-{name}"
            values[token] = {"type": "number", "value": value}
            roles["canvas-overlay-gradient"][name] = token
    return ThemeTokenView(themed)


def test_review_surface_carries_both_completed_overlays_on_the_final_canvas():
    request = replace(_axis_request(()), theme_tokens=_theme_with_overlays())

    placement = compose_surface_layout(request).placement

    overlays = placement.canvas_overlays
    assert overlays is not None and overlays.pattern is not None and overlays.radial is not None
    assert overlays.pattern.slot.bounds == overlays.radial.slot.bounds == placement.canvas_bounds
    assert overlays.pattern.pattern.region == overlays.pattern.pattern.clip == placement.canvas_bounds
    assert overlays.radial.center == (
        placement.canvas_bounds.inline + placement.canvas_bounds.inline_size / 2,
        placement.canvas_bounds.block + placement.canvas_bounds.block_size / 2,
    )


def test_review_surface_keeps_overlay_closure_absent_without_theme_roles():
    placement = compose_surface_layout(_axis_request(())).placement
    assert placement.canvas_overlays is None


def test_dependency_network_carries_overlay_geometry_without_changing_canvas_or_routes():
    tokens = _theme_with_overlays()
    network = _network(("a", "b"), (("ab", "a", "b"),))
    kwargs = dict(
        title_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40)),
        bounds=Rect(Decimal(0), Decimal(40), Decimal(400), Decimal(160)),
        measured_sources=_measured("a", "b"), flow_direction="horizontal",
        canvas_bounds=Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(200)), theme_tokens=tokens,
    )

    layout = compose_dependency_network_layout(network, **kwargs)
    plain = compose_dependency_network_layout(
        network, **{**kwargs, "theme_tokens": _theme_with_overlays(pattern=False, radial=False)})

    assert layout.canvas_bounds == plain.canvas_bounds == kwargs["canvas_bounds"]
    assert layout.nodes == plain.nodes and layout.relations == plain.relations
    assert layout.canvas_overlays is not None
    assert layout.canvas_overlays.pattern.slot.bounds == layout.canvas_bounds
    assert layout.canvas_overlays.pattern.pattern.region == layout.canvas_overlays.pattern.pattern.clip == layout.canvas_bounds
    assert layout.canvas_overlays.radial.slot.bounds == layout.canvas_bounds
    assert plain.canvas_overlays is None
