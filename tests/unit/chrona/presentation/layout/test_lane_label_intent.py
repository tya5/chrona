from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.lane_label_intent import measure_lane_member_labels
from chrona.presentation.layout.surface_quality import VisualRequest


class _Metrics:
    def select(self, _family, _weight):
        return self

    def width(self, content, size, **kwargs):
        return len(content) * size + len(content) * kwargs.get("letter_spacing", 0)


class _Theme:
    def text_treatment(self, _role):
        return SimpleNamespace(family="Test", weight=400, font_size=Decimal(10),
                               line_height=Decimal("1.2"), letter_spacing=Decimal(0),
                               transform="none", numeric_spacing="proportional", horizontal_scale=Decimal(1))

    def icon_ratios(self, _role):
        return Decimal("0.5"), Decimal("0.2")

    def label_chip(self, _role):
        return (Decimal("0.1"), Decimal(0))

    def label_chip_min_block(self, _role):
        return None

    def label_chip_shape(self, _role):
        from chrona.presentation.model.theme_tokens import RectangleChipShape
        return RectangleChipShape()


@dataclass(frozen=True)
class _Item:
    object_id: str
    item_id: str
    title: str
    finish_delta: int | None = None
    source_kind: str = "primary"
    attached_to: str | None = None
    presentation: dict | None = None


def _inputs(items, member_ids=None, *, attached=(), fallback=("start", "end")):
    member_ids = member_ids or tuple(item.item_id for item in items)
    projection = SimpleNamespace(
        rows=(SimpleNamespace(row_id="source-row", items=tuple(items)),),
        lane_rows=(SimpleNamespace(lane_id="lane-a", items=tuple(items),
                                   member_item_ids=tuple(member_ids)),),
    )
    content = SimpleNamespace(show_member_labels=True, label_content=("title", "finishDelta"),
                              label_side="auto", label_fallback=fallback, label_text_role=None,
                              attached_labels=tuple(attached))
    return projection, content


def test_normalizes_attached_text_before_title_and_delta_and_preserves_identity():
    item = _Item("gate", "gate-instance", "Gate", 3, attached_to="host")
    projection, content = _inputs((item,), attached=(("gate", "Gate date +3d"),))

    (measured,) = measure_lane_member_labels(
        projection, content, timeline_inline_size=100, theme_tokens=_Theme(),
        font_metrics=_Metrics(), visual_requests=(), icon_assets={},
    )

    assert measured.placement_id == "member-label:lane-a:gate-instance"
    assert (measured.source_ref, measured.lane_id, measured.member_id, measured.source_kind) == (
        "gate", "lane-a", "gate-instance", "primary")
    assert measured.content == "Gate date +3d"
    assert measured.candidates == ("start", "end")


def test_measures_wrap_font_icons_and_chip_padding_as_one_box():
    item = _Item("task", "task", "Long task name", 2,
                 presentation={"text": {"wrap": "allow"}})
    projection, content = _inputs((item,))
    visuals = (
        VisualRequest("plot-label", (("placementId", "member-label:lane-a:task"),),
                      ref="wide", side="leading"),
        VisualRequest("plot-label", (("placementId", "member-label:lane-a:task"),),
                      ref="wide", side="trailing"),
    )
    icon = SimpleNamespace(viewport=(2, 1))

    (measured,) = measure_lane_member_labels(
        projection, content, timeline_inline_size=50, theme_tokens=_Theme(),
        font_metrics=_Metrics(), visual_requests=visuals, icon_assets={"wide": icon},
    )

    assert measured.lines == ("Long", "task", "name", "+2d")
    assert measured.wrap == "allow"
    assert measured.chip_padding == (1.0, 0.5)
    assert measured.text_inline_inset == 13.0  # chip padding plus leading icon width (10) and gap (2)
    assert measured.gap == 2.5
    assert measured.width == 66.0  # text 40 + two icon runs (12 each) + chip padding (2)
    assert measured.height == 49.0  # four 12-unit lines plus vertical chip padding
    assert (measured.font_family, measured.font_weight, measured.font_size) == ("Test", 400, 10.0)
    assert (measured.leading_advance, measured.trailing_advance) == (12.0, 12.0)
    assert len(measured.visuals) == 2
