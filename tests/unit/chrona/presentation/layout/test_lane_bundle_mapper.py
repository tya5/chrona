from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.lane_bundle_mapper import (
    _mark_facets, preflight_review_lanes,
)
from chrona.presentation.layout.lane_projection import LaneProjectionInstance
from chrona.presentation.layout.lane_preflight import LaneInlineFrame, LaneMeasurementIdentity
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.surface_quality import MarkPlacement, ScalePlacement, VisualRequest
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection


class _Theme:
    def optional_number(self, role, name):
        return Decimal("2") if name == "strokeWidth" else None


class _LaneTheme(_Theme):
    def text_treatment(self, _role):
        return SimpleNamespace(
            family="Test Sans", weight=400, font_size=Decimal("10"),
            line_height=Decimal("1.2"), letter_spacing=Decimal("0"),
            transform="uppercase", numeric_spacing="proportional",
            paint_content=lambda content: content.upper(),
        )

    def icon_ratios(self, _role):
        return Decimal("0.5"), Decimal("0.2")


class _Metrics:
    content_identity = "sha256:lane-font"

    def select(self, _family, _weight):
        return self

    def width(self, content, size, **_kwargs):
        return len(content) * size / 2


def test_review_projection_closes_candidate_and_preflight_with_measured_title_delta_visual():
    item = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        None, 2, ("planned",), group_id="systems", item_id="work-view",
        source_kind="primary",
    )
    row = ReviewRowProjection("row-1", "Work", "systems", "work-view", (item,))
    projection = ReviewProjection(
        (item,), (date(2026, 1, 1), date(2026, 2, 1)), (), (), rows=(row,),
    )
    instance = LaneProjectionInstance("row-1", "work-view", "work", "primary")
    visual = VisualRequest(
        "plot-label", (("id", "work"),), ref="task-icon",
        side="leading", source_ref="/body/visuals/0",
    )
    icon = SimpleNamespace(
        icon_id="task-icon", kind="vector", content_identity="sha256:task-icon",
        viewport=(20, 10), payload=(), alternative="Task icon",
    )
    scale = ScalePlacement(
        "timeline", "scale:lane", date(2026, 1, 1), date(2026, 2, 1),
        0, 100, 0, 2,
    )
    frame = MarkBandFrame.zero_origin(scale, 10, {
        "planned": MarkGeometry(0.4, 0.1, 0, 0),
        "actual": MarkGeometry(0.4, 0.5, 1, 0),
        "missing-actual": MarkGeometry(0.4, 0.5, 2, 0),
    })
    identity = LaneMeasurementIdentity("sha256:theme", _Metrics.content_identity, "scale:lane")

    mapped, plan = preflight_review_lanes(
        projection, frame=frame, as_of=None, theme_tokens=_LaneTheme(), slot_id="lane-slot",
        measurement_identity=identity, font_metrics=_Metrics(),
        label_visual_requests={}, view_visual_requests=(visual,),
        icon_assets={"task-icon": icon},
        include_finish_delta=True, label_typography_role="text",
        seed_inline_frame=LaneInlineFrame(
            Decimal("0"), Decimal("30"), Decimal("30"), Decimal("100"), Decimal("2"),
        ),
        group_titles={"systems": "Systems"}, lane_label="group", include_count=True,
        mark_row_height=10, label_row_height=12,
    )

    assert len(mapped.candidates) == 1
    member = mapped.candidates[0].members_for_placement[0]
    label = member.required_label
    assert label is not None
    assert label.title == "Work" and label.delta == "+2d"
    assert label.normalized_content == "WORK +2D"
    assert len(label.leading_visuals) == 1
    assert label.leading_visuals[0].measured_bounds.inline == 0
    assert {facet.purpose for facet in member.mark.facets} == {"planned"}
    assert mapped.expected_facets[0].primitive_id == "planned:row-1:work-view"
    assert plan.candidates == mapped.candidates
    assert plan.table_cells[0].count == 1


def test_mapper_closes_span_as_source_keyed_plain_facet_with_ports_and_footprint():
    item = ReviewItem(
        "work", "Work", "span",
        {"start": date(2026, 1, 1), "end": date(2026, 1, 4)},
        None, None, ("planned",), item_id="work-view", source_kind="primary",
    )
    instance = LaneProjectionInstance("row:1", "work-view", "work", "primary")
    mark = MarkPlacement(
        "planned:row%3A1:work-view", "work",
        Rect(Decimal("10"), Decimal("1"), Decimal("20"), Decimal("4")),
        (10, 3), (30, 3), mark_shape="span", semantic_id="planned",
        paint_order=7,
    )

    facets = _mark_facets(item, instance, mark, _Theme())

    assert len(facets) == 1
    facet = facets[0]
    assert facet.projection_instance_id == instance.placement_key
    assert facet.source_item_id == "work-view"
    assert facet.source_ref == "work"
    assert facet.visible_footprint == ObstacleRect(9, 0, 31, 6)
    assert tuple(port.purpose for port in facet.ports) == ("start", "end")
    assert facet.plain_mark_projection.shape == "span"
    assert facet.plain_mark_projection.paint_order == 7
