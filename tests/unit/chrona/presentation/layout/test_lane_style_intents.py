from datetime import date
from decimal import Decimal

from chrona.presentation.layout import lane_item_footprints as owner
from chrona.presentation.layout.lane_item_footprints import compose_lane_item_footprints
from chrona.presentation.layout.presentation import MarkGeometry
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrence, MarkOccurrenceKind, build_item_mark_visibility_index,
)
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.model.projection import (
    ReviewItem, ReviewLaneRowProjection, ReviewProjection, ReviewRowProjection,
)
from chrona.presentation.model.style_rules import (
    OccurrenceStyleIndex, OccurrenceStyleIntent, StyleOccurrenceKey,
)
from chrona.presentation.review.lane_membership import Lane, LaneAssignment, LaneMembership


class _Theme:
    def optional_number(self, _role, name):
        return {"custom-work-mark": 8, "planned": 2}.get(_role) if name == "strokeWidth" else None

    def mark_geometry(self, role):
        return ((Decimal("0.8") if role == "custom-work-mark" else Decimal("0.4")),
                None, 0, Decimal(0))

    def symbol_geometry(self, _role):
        return None, None

    def optional_token(self, _role, _name, _expected):
        return None

    def mark_alignment(self, _role):
        return "center"

    def mark_stack(self):
        return None


def test_lane_footprint_joins_each_intent_to_original_source_occurrence(monkeypatch):
    day = date(2026, 1, 1)
    item = ReviewItem("work", "Work", "span", {"start": day, "end": date(2026, 1, 3)},
                      None, None, ("planned",), item_id="work-row-item", source_kind="primary")
    row_id = "lane-source-row"
    membership = LaneMembership((Lane("lane", "group", (item.item_id,)),), (
        LaneAssignment(item.item_id, "lane", "group", "dates", "fixed"),
    ))
    projection = ReviewProjection(
        (item,), (day, date(2026, 1, 5)), (), (),
        rows=(ReviewRowProjection(row_id, "Work", "group", item.item_id, (item,)),),
        lane_membership=membership,
        lane_rows=(ReviewLaneRowProjection("lane", "group", (item,), (item.item_id,)),),
    )
    source = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, row_id, item.item_id,
                            item.object_id, item.source_kind)
    key = source.style_key("planned")
    intent = OccurrenceStyleIntent(key, "custom-work-mark", None, ("rule-work",),
                                   ("rule-work",), ())
    index = OccurrenceStyleIndex((intent,))
    visibility = build_item_mark_visibility_index(projection, as_of=None)
    captured_marks = []
    mark_facets = owner._mark_facets

    def capture_mark_facets(source_item, instance, mark, theme):
        captured_marks.append(mark)
        return mark_facets(source_item, instance, mark, theme)

    monkeypatch.setattr(owner, "_mark_facets", capture_mark_facets)
    footprints = compose_lane_item_footprints(
        projection,
        scale=ScalePlacement("timeline", "scale", day, date(2026, 1, 5), 0, 40, 0, 10),
        as_of=None, theme_tokens=_Theme(), mark_band_size=10,
        role_geometries={role: MarkGeometry(.4, .1, 0, 0)
                         for role in ("planned", "actual", "missing-actual")},
        slot_id="timeline", icon_assets={}, mark_visibility_index=visibility,
        style_intents=index,
    )

    assert len(footprints) == 1 and len(footprints[0].facets) == 1
    facet = footprints[0].facets[0]
    assert facet.footprint.bottom - facet.footprint.top == 16
    assert len(captured_marks) == 1
    assert captured_marks[0].theme_role == "custom-work-mark"
    assert captured_marks[0].style_occurrence_key == key
    assert key == StyleOccurrenceKey("work", "primary", "planned", row_id,
                                     "work-row-item", occurrence_kind="lane-source")


def test_lane_style_roles_are_used_for_theme_stroke_lookup_without_rewriting_semantics():
    from chrona.presentation.layout.lane_mark_facets import _mark_facets
    from chrona.presentation.layout.lane_projection import LaneProjectionInstance
    from chrona.presentation.layout.model import Rect

    class Theme:
        def optional_number(self, role, name):
            assert name == "strokeWidth"
            return {"planned": 2, "custom-work-mark": 8}[role]

    class Mark:
        placement_id = "planned:work"
        semantic_id = "planned"
        theme_role = "custom-work-mark"
        style_occurrence_key = StyleOccurrenceKey(
            "work", "primary", "planned", "row", "work-row-item",
            occurrence_kind="lane-source",
        )
        bounds = Rect(10, 5, 20, 4)
        start_port = None
        end_port = None
        paint_clip = None
        mark_shape = "span"
        symbol_parts = ()
        path_commands = ()
        paint_order = 100
        corner_radius = 0
        end_treatment = "closed"

    item = ReviewItem("work", "Work", "span", {}, None, None, ("planned",),
                      item_id="work-row-item", source_kind="primary")
    mark = Mark()
    facets = _mark_facets(item, LaneProjectionInstance("row", item.item_id,
                         item.object_id, item.source_kind), mark, Theme())

    footprint = facets[0].visible_footprint
    assert (footprint.left, footprint.top, footprint.right, footprint.bottom) == (6, 1, 34, 13)
    assert facets[0].plain_mark_projection.semantic_role == "planned"
    assert facets[0].plain_mark_projection.theme_role == "custom-work-mark"
    assert facets[0].plain_mark_projection.style_occurrence_key == Mark.style_occurrence_key
