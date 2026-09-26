from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_composer import _completed_canvas, resolve_text_visual_requests, visual_target_placement_id
from chrona.presentation.layout.surface_quality import TextPlacement, VisualRequest


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
    placed, icons, warnings = resolve_text_visual_requests([item], request)
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
        resolve_text_visual_requests([item], request)


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
    placed, _, warnings = resolve_text_visual_requests([item], request)
    assert placed[0].content == "Long" and placed[0].overflow == "visible-overflow"
    assert len(warnings) == 1 and warnings[0].required_inline > allocated
