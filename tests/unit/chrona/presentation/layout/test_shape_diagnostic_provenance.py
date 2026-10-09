"""Non-text geometry carries its declared semantic owner without ID inference."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.presentation import MarkGeometry, TrackPlacement
from chrona.presentation.layout.surface_deadlines import compose_deadline_marks
from chrona.presentation.layout.surface_marks import compose_surface_marks
from chrona.presentation.layout.surface_member_labels import (
    SurfaceMemberLabelContext, place_member_labels,
)
from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, MarkPlacement, ScalePlacement, SlotPlacement,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.projection import ReviewDeadline


class _Metric:
    content_identity = "sha256:test-font"

    def width(self, value, size, **_kwargs):
        return len(value) * size

    def cap_height_at(self, size):
        return size * .7


class _Theme:
    def text_treatment(self, _role):
        return SimpleNamespace(family="Test", weight=400, font_size=10, line_height=1.2,
                               letter_spacing=0, transform="none", numeric_spacing="proportional",
                               horizontal_scale=1)

    def label_chip(self, _role):
        return (0.2, 0.1)

    def label_chip_min_block(self, _role):
        return None

    def optional_token(self, *_args):
        return None

    def icon_ratios(self, _role):
        return (Decimal(1), Decimal("0.2"))

    def progress_track(self, _role):
        return (Decimal(0), Decimal(0))


def test_progress_fill_uses_exact_projection_item_subject_not_source_or_mark_instance_id():
    day0, day1 = date(2026, 1, 1), date(2026, 1, 11)
    item = SimpleNamespace(object_id="project-owner-7", title="Selected row subject", item_id="instance-7",
                           source_kind="primary", source_type="span",
                           planned={"start": day0, "end": day1}, actual={}, planned_progress=.5,
                           observation_state="unavailable", missing_actual_mark="due-end")
    row = SimpleNamespace(row_id="row-7", items=(item,), rollup_presentation="none")
    projection = SimpleNamespace(rows=(row,), lane_membership=None, folded_points=())
    scale = ScalePlacement("surface", "time", day0, day1, 0, 100, 0, 10)
    track = TrackPlacement("row-7:instance-7", 10, 10, 20)
    timeline = SlotPlacement("timeline", "timeline", Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(80)))
    roles = {name: MarkGeometry(.5, .25, index, 0)
             for index, name in enumerate(("planned", "actual", "missing-actual"))}
    request = SimpleNamespace(
        projection=projection, presentation_contract=SimpleNamespace(time=SimpleNamespace(as_of=None)),
        theme_tokens=_Theme(), surface_content=SimpleNamespace(progress_fill_source="planned"),
    )
    base = SimpleNamespace(
        request=request, review_rows=(row,), rows=(SimpleNamespace(row_id="row-7"),),
        tracks=(track,), scale=scale, timeline=timeline, role_geometries=roles,
        mark_block_size=20, groups=(), mark_band_allocation=None,
    )

    batch = compose_surface_marks(base, lane_owner=lambda _row, _item: None)

    progress = batch.progress_shapes[0]
    assert progress.source_ref == item.object_id
    assert progress.placement_id == "progress-fill:planned:row-7:instance-7"
    assert progress.subjects == (DiagnosticSubject.project_object(item.object_id, item.title),)


def test_member_chip_inherits_label_request_subject_not_label_or_row_id():
    subject = DiagnosticSubject.project_object("project-owner-9", "Declared table subject")
    timeline = SlotPlacement("timeline", "timeline", Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(100)))
    request = SimpleNamespace(theme_tokens=_Theme(), font_metrics=_Metric(), visual_requests=(), icon_assets={},
                              fixed_lane_preflight=None)
    context = SurfaceMemberLabelContext(
        request=request, projection=SimpleNamespace(lane_membership=None),
        layout_manifest=SimpleNamespace(member_names={}, row_distribution="auto"),
        by_source={"timeline": timeline}, text_slot=lambda _text: "timeline",
        review_rows=(), rows=(), tracks=(), groups=(), scale=None, marks=(),
        timeline_bounds=(0, 0, 100, 100), as_of_label=None,
    )
    label = LabelRequest("member-label:row-9", "row-9", "Owner", LabelRect(20, 20, 10, 10),
        ("end",), "text", "plot-label", CollisionDomain("timeline", "overlay"),
        "visible-overflow", semantic_id="memberLabel", subjects=(subject,))

    batch = place_member_labels(context, (label,), SurfaceObstacleIndex())

    chip = batch.shapes[0]
    assert chip.placement_id == "chip:member-label:row-9"
    assert chip.source_ref == "row-9"
    assert chip.subjects == (subject,)
    assert chip.subjects[0].source_ref == "/objects/project-owner-9"


def test_deadline_shapes_inherit_typed_host_subject_for_ticks_and_runs():
    deadline_day, finish_day = date(2026, 1, 5), date(2026, 1, 8)
    subject = DiagnosticSubject.project_object("project/11", "Deadline owner")
    host = MarkPlacement("planned:row-11:instance-11", "project/11",
        Rect(Decimal(20), Decimal(30), Decimal(40), Decimal(10)), (20, 35), (60, 35),
        slot_id="timeline", semantic_id="planned", subjects=(subject,))
    base = SimpleNamespace(
        plot=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(100)),
        scale=ScalePlacement("surface", "time", date(2026, 1, 1), date(2026, 1, 11), 0, 100, 0, 10),
    )
    theme = SimpleNamespace(deadline_mark=lambda _role: (.8, 4))

    result = compose_deadline_marks(base=base, theme_tokens=theme,
        deadlines=(ReviewDeadline("project/11", deadline_day, finish_day, True),),
        marks=(host,), window=(date(2026, 1, 1), date(2026, 1, 11)), paint_order_base=120)

    assert [shape.placement_id for shape in result.shapes] == [
        "deadline-tick:row-11:instance-11", "deadline-run:row-11:instance-11"]
    assert all(shape.source_ref == "project/11" and shape.subjects == (subject,)
               for shape in result.shapes)
