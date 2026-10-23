from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.lane_label_intent import measure_lane_member_labels
from chrona.presentation.model.hierarchy_names import member_name_key
from chrona.presentation.model.projection import ReviewItem, ReviewLaneRowProjection, ReviewProjection, ReviewRowProjection
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
    scenario_id: str | None = None


def _inputs(items, member_ids=None, *, attached=(), fallback=("start", "end"), name=None):
    member_ids = member_ids or tuple(item.item_id for item in items)
    projection = SimpleNamespace(
        rows=(SimpleNamespace(row_id="source-row", items=tuple(items)),),
        lane_rows=(SimpleNamespace(lane_id="lane-a", items=tuple(items),
                                   member_item_ids=tuple(member_ids)),),
    )
    content = SimpleNamespace(show_member_labels=True, label_content=("title", "finishDelta"),
                              label_side="auto", label_fallback=fallback, label_text_role=None,
                              omit_zero_delta=False,
                              attached_labels=tuple((member_name_key(item, "lane-a"), text)
                                                   for object_id, text in attached for item in items
                                                   if item.object_id == object_id),
                              member_name=name or (lambda item, _container_id="": item.title))
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


def test_lane_preflight_uses_closed_member_name_for_both_legacy_and_path_names():
    item = _Item("leaf", "leaf-instance", "Leaf", 3)

    projection, legacy_content = _inputs((item,))
    (legacy,) = measure_lane_member_labels(
        projection, legacy_content, timeline_inline_size=100, theme_tokens=_Theme(),
        font_metrics=_Metrics(), visual_requests=(), icon_assets={},
    )

    projection, path_content = _inputs(
        (item,), name=lambda _item, container_id: "Program / Release / Leaf"
        if container_id == "lane-a" else "unexpected",
    )
    (path,) = measure_lane_member_labels(
        projection, path_content, timeline_inline_size=100, theme_tokens=_Theme(),
        font_metrics=_Metrics(), visual_requests=(), icon_assets={},
    )

    assert legacy.content == "Leaf +3d"
    assert path.content == "Program / Release / Leaf +3d"
    assert path.width > legacy.width
    assert path.placement_id == legacy.placement_id
    assert path.source_ref == legacy.source_ref


def test_attached_composites_are_selected_by_source_occurrence_not_object_id():
    from datetime import date

    primary = ReviewItem("gate", "Primary title", "point", {"at": date(2026, 1, 2)},
        {"at": date(2026, 1, 3)}, 1, (), item_id="primary-gate", source_kind="primary",
        attached_to="host")
    snapshot = ReviewItem("gate", "Snapshot title", "point", {"at": date(2026, 2, 4)},
        {"at": date(2026, 2, 7)}, 3, (), item_id="snapshot-gate", source_kind="snapshot",
        attached_to="host")
    lane_id = "lane-shared"
    projection = ReviewProjection((primary, snapshot),
        (date(2026, 1, 1), date(2026, 3, 1)), (), (),
        rows=(ReviewRowProjection("source-row", "", "", primary.item_id, (primary, snapshot)),),
        lane_membership=object(), lane_rows=(ReviewLaneRowProjection(
            lane_id, "", (primary, snapshot), (primary.item_id, snapshot.item_id)),))
    content = SimpleNamespace(show_member_labels=True, label_content=("title",),
        label_side="auto", label_fallback=("start", "end"), label_text_role=None,
        omit_zero_delta=False,
        attached_labels=(
            (member_name_key(primary, lane_id), "Primary program / Primary approval · 02 Jan · +1d"),
            (member_name_key(snapshot, lane_id), "Archived program / Snapshot approval · 04 Feb · +3d"),
        ), member_name=lambda item, _container_id="": item.title)

    measured = measure_lane_member_labels(
        projection, content, timeline_inline_size=200, theme_tokens=_Theme(),
        font_metrics=_Metrics(), visual_requests=(), icon_assets={},
    )

    assert [(label.source_ref, label.content) for label in measured] == [
        ("gate", "Primary program / Primary approval · 02 Jan · +1d"),
        ("gate", "Archived program / Snapshot approval · 04 Feb · +3d"),
    ]
    assert len({label.placement_id for label in measured}) == 2
