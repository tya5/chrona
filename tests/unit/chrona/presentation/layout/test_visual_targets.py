from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.label_visual_measurement import visual_target_placement_id
from chrona.presentation.layout.surface_composer import _completed_canvas
from chrona.presentation.layout.surface_visuals import (
    place_axis_band_visuals, place_mark_visuals, place_text_visuals,
)
from chrona.presentation.layout.surface_quality import MarkPlacement, ShapePlacement, TextPlacement, VisualRequest


@pytest.mark.parametrize(("kind", "selector", "expected"), [
    ("title", {}, "title"), ("column", {"id": "owner"}, "column:owner"),
    ("cell", {"object": "risk", "column": "owner"}, "cell:risk:owner"),
    ("annotation", {"id": "callout"}, "annotation-text:callout"),
    ("note", {"id": "scope"}, "note:scope"),
    ("group-detail", {"id": "firmware"}, "group-detail:firmware"),
    ("summary", {"panel": "key", "metric": "launch", "part": "value"}, "summary:key:launch:value"),
    ("variance-label", {"object": "risk"}, "variance:risk"),
    ("as-of-label", {}, "as-of-label"),
])
def test_visual_target_maps_only_to_existing_layout_identity(kind, selector, expected):
    assert visual_target_placement_id(kind, selector) == expected


def test_visual_target_rejects_incomplete_selector():
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        visual_target_placement_id("cell", {"object": "risk"})


def test_axis_visual_target_requires_layout_tier_metadata():
    with pytest.raises(LayoutError, match="E_LAYOUT_VISUAL_TARGET"):
        visual_target_placement_id("axis-label", {"level": "month", "index": "2"})


def test_text_and_two_visuals_keep_natural_width_when_slot_is_smaller_than_icons():
    class Metric:
        def width(self, value, size, **_kwargs):
            return len(value) * size

        def cap_height_at(self, size):
            return size * .7

    visual = SimpleNamespace(icon_id="test", kind="icon", content_identity="sha256:test",
                             viewport=(10, 10), payload=(), alternative="test")
    request = SimpleNamespace(
        visual_requests=(VisualRequest("title", (), ref="icon", side="leading"),
                         VisualRequest("title", (), ref="icon", side="trailing")),
        icon_assets={"icon": visual}, font_metrics=Metric(),
        theme_tokens=SimpleNamespace(icon_ratios=lambda _role: (Decimal(1), Decimal("0.2"))),
    )
    item = TextPlacement("title", "title", "Long", Rect(Decimal(0), Decimal(0), Decimal(5), Decimal(12)),
                         "text", baseline=(0, 10), lines=("Long",), font_family="Test", font_weight=400,
                         font_size=10, line_height=1.2, available_inline_start=0, available_inline_size=5)
    batch = place_text_visuals((item,), request)
    placed, icons, warnings = list(batch.text), list(batch.icons), list(batch.warnings)
    assert placed[0].content == "Long" and placed[0].overflow == "visible-overflow"
    assert len(icons) == 2 and icons[0].bounds.inline == 0
    assert icons[1].bounds.inline >= placed[0].bounds.inline + placed[0].bounds.inline_size
    assert len(warnings) == 1 and warnings[0].required_inline > warnings[0].available_inline
    canvas = _completed_canvas(requested=Rect(Decimal(0), Decimal(0), Decimal(5), Decimal(12)),
                               rectangles=tuple([placed[0].bounds, *(icon.bounds for icon in icons)]), paths=())
    assert canvas.inline_size > 5


def test_completed_canvas_includes_negative_origin_geometry():
    canvas = _completed_canvas(requested=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(50)),
                               rectangles=(Rect(Decimal(-12), Decimal(-4), Decimal(8), Decimal(8)),), paths=())
    assert canvas == Rect(Decimal(-12), Decimal(-4), Decimal(112), Decimal(54))


def test_zero_icon_scale_is_invalid_theme_input_not_fit_shortage():
    visual = SimpleNamespace(icon_id="test", kind="icon", content_identity="sha256:test",
                             viewport=(10, 10), payload=(), alternative="test")
    request = SimpleNamespace(
        visual_requests=(VisualRequest("title", (), ref="icon"),), icon_assets={"icon": visual},
        font_metrics=SimpleNamespace(width=lambda _value, _size: 10),
        theme_tokens=SimpleNamespace(icon_ratios=lambda _role: (Decimal(0), Decimal(0))),
    )
    item = TextPlacement("title", "title", "A", Rect(Decimal(0), Decimal(0), Decimal(50), Decimal(12)),
                         "text", baseline=(0, 10), lines=("A",), font_family="Test", font_weight=400,
                         font_size=10, line_height=1.2)
    with pytest.raises(LayoutError, match="E_THEME_ICON_RATIO"):
        place_text_visuals((item,), request)


@pytest.mark.parametrize("allocated", [5, 17])
def test_required_text_is_not_erased_when_icon_leaves_less_than_ellipsis_width(allocated):
    class Metric:
        def width(self, value, size, **_kwargs):
            return len(value) * size

        def cap_height_at(self, size):
            return size * .7

    icon = SimpleNamespace(icon_id="test", kind="icon", content_identity="sha256:test",
                           viewport=(10, 10), payload=(), alternative="test")
    request = SimpleNamespace(
        visual_requests=(VisualRequest("title", (), ref="icon"),), icon_assets={"icon": icon},
        font_metrics=Metric(),
        theme_tokens=SimpleNamespace(icon_ratios=lambda _role: (Decimal(1), Decimal("0.2"))),
    )
    item = TextPlacement("title", "title", "…", Rect(Decimal(0), Decimal(0), Decimal(allocated), Decimal(12)),
                         "text", baseline=(0, 10), lines=("…", "…"), font_family="Test", font_weight=400,
                         font_size=10, line_height=1.2, source_content="Long",
                         available_inline_start=0, available_inline_size=allocated)
    batch = place_text_visuals((item,), request)
    placed, warnings = list(batch.text), list(batch.warnings)
    assert placed[0].content == "Long" and placed[0].overflow == "visible-overflow"
    assert len(warnings) == 1 and warnings[0].required_inline > allocated


def _icon_request(visual_request):
    icon = SimpleNamespace(icon_id="test", kind="icon", content_identity="sha256:test",
                           viewport=(10, 10), payload=(), alternative="test")
    return SimpleNamespace(visual_requests=(visual_request,), icon_assets={"icon": icon},
                           theme_tokens=SimpleNamespace(
                               icon_ratios=lambda _role: (Decimal("0.5"), Decimal("0.2"))))


def test_mark_visual_is_hosted_on_completed_mark_and_preserves_lane_identity():
    request = _icon_request(VisualRequest("mark", (("object", "task"), ("facet", "planned")),
                                          ref="icon"))
    host = MarkPlacement("planned:task", "task", Rect(Decimal(10), Decimal(20),
        Decimal(20), Decimal(10)), (10, 25), (30, 25), slot_id="timeline",
        paint_order=100, lane_row_id="row", lane_member_id="member")
    batch = place_mark_visuals((host,), request)
    assert len(batch.icons) == 1
    icon = batch.icons[0]
    assert icon.host_placement_id == host.placement_id
    assert icon.paint_order == host.paint_order + 1
    assert icon.slot_id == host.slot_id
    assert (icon.lane_row_id, icon.lane_member_id) == ("row", "member")
    assert icon.bounds == Rect(Decimal("17.5"), Decimal("22.5"), Decimal(5), Decimal(5))


def test_axis_band_visual_uses_completed_shape_target_slot_and_host_order():
    request = _icon_request(VisualRequest("axis-band", (("level", "quarter"), ("index", "0")),
                                          ref="icon"))
    host = ShapePlacement("axis-band:quarter:0", "timeline-axis", "Rect",
        Rect(Decimal(10), Decimal(20), Decimal(20), Decimal(12)), slot_id="axis",
        paint_order=100, semantic_id="axisQuarterBand")
    batch = place_axis_band_visuals((host,), request,
        targets={("axis-band", "quarter", "0"): host.placement_id})
    assert len(batch.icons) == 1
    icon = batch.icons[0]
    assert icon.placement_id == f"visual:{host.placement_id}"
    assert icon.source_ref == host.source_ref
    assert icon.slot_id == "axis"
    assert icon.paint_order == 200
    assert icon.bounds == Rect(Decimal(17), Decimal(23), Decimal(6), Decimal(6))
