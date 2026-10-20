from decimal import Decimal
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_deadlines import _outline, compose_deadline_marks, deadline_boundary_in_window
from chrona.presentation.layout.surface_geometry import coordinate_for_date, coordinate_for_day_ordinal
from chrona.presentation.layout.surface_quality import MarkPlacement, ScalePlacement, ShapePlacement
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.projection import ReviewDeadline


def test_completed_ordinals_map_and_admit_without_constructing_a_date_after_date_max():
    start = date(9999, 12, 30)
    scale = ScalePlacement("surface", "time", start, date.max, 0, 10, 0, 10)
    assert coordinate_for_day_ordinal(date.max.toordinal() + 1, scale) == 20
    assert coordinate_for_date(date.max, scale) == 10
    shown = ReviewDeadline("owner", start, date.max.toordinal(), date.max.toordinal() + 1, True, 1)
    assert deadline_boundary_in_window(shown, (start, date.max))
    outside = ReviewDeadline("owner", date.max, date.max.toordinal() + 1, date.max.toordinal() + 1, False, 0)
    assert not deadline_boundary_in_window(outside, (start, date.max))


@pytest.mark.parametrize("points,expected", [
    (((10, 20), (10, 30)), (8, 18, 4, 14)),
    (((10, 30), (40, 30)), (8, 28, 34, 4)),
])
def test_outline_completes_ground_bounds_order_and_provenance(points, expected):
    subject = DiagnosticSubject.project_object("owner", "Deadline owner")
    stroke = ShapePlacement("deadline-tick:owner", "owner", "Path",
                            Rect(Decimal(10), Decimal(20), Decimal(0), Decimal(10)), points,
                            slot_id="timeline", paint_order=105, semantic_id="deadlineMark", subjects=(subject,))
    ground = _outline(stroke, 2)
    assert ground is not None
    assert ground.bounds == Rect(*(Decimal(value) for value in expected))
    assert ground.kind == "Rect" and ground.points == ()
    assert ground.semantic_id == "deadlineMarkOutline" and ground.paint_order == 104
    assert ground.placement_id == stroke.placement_id + ":outline"
    assert ground.source_ref == stroke.source_ref and ground.subjects == stroke.subjects
    assert ground.slot_id == stroke.slot_id and ground.paint_clip == stroke.paint_clip


def test_zero_length_stroke_has_no_phantom_opaque_ground():
    stroke = ShapePlacement("deadline-run:owner", "owner", "Path",
                            Rect(Decimal(10), Decimal(20), Decimal(0), Decimal(0)),
                            ((10, 20), (10, 20)), semantic_id="deadlineMark")
    assert _outline(stroke, 2) is None


@pytest.mark.parametrize("stroke_width,expected_grounds", [(0, 0), (2, 2)])
def test_invisible_stroke_adds_no_ground_but_visible_tick_and_run_do(stroke_width, expected_grounds):
    base = SimpleNamespace(
        plot=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(100)),
        scale=ScalePlacement("surface", "time", date(2026, 1, 1), date(2026, 1, 11), 0, 100, 0, 10))
    host = MarkPlacement("planned:owner", "owner",
                         Rect(Decimal(20), Decimal(30), Decimal(40), Decimal(10)),
                         (20, 35), (60, 35), semantic_id="planned", slot_id="timeline")
    tokens = SimpleNamespace(deadline_mark=lambda _role: (1.7, 5),
                             deadline_outline_width=lambda _role: 1,
                             wobble_intent=lambda _role: None,
                             number=lambda _role, _property: stroke_width)
    batch = compose_deadline_marks(base=base, theme_tokens=tokens,
        deadlines=(ReviewDeadline("owner", date(2026, 1, 5), date(2026, 1, 6).toordinal(), date(2026, 1, 9).toordinal(), True, 3),),
        marks=(host,), window=(date(2026, 1, 1), date(2026, 1, 11)), paint_order_base=100)
    assert sum(shape.semantic_id == "deadlineMarkOutline" for shape in batch.shapes) == expected_grounds
    assert sum(shape.semantic_id == "deadlineMark" for shape in batch.shapes) == 2


def test_caption_anchor_uses_the_same_completed_maximum_wobble_envelope():
    base = SimpleNamespace(
        plot=Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(100)),
        scale=ScalePlacement("surface", "time", date(2026, 1, 1), date(2026, 1, 11), 0, 100, 0, 10))
    subject = DiagnosticSubject.project_object("owner")
    host = MarkPlacement("planned:owner", "owner",
                         Rect(Decimal(20), Decimal(30), Decimal(40), Decimal(10)),
                         (20, 35), (60, 35), semantic_id="planned", slot_id="timeline", subjects=(subject,))
    tokens = SimpleNamespace(deadline_mark=lambda _role: (1.7, 5),
                             deadline_outline_width=lambda _role: 1,
                             wobble_intent=lambda _role: SimpleNamespace(amplitude=4),
                             number=lambda _role, _property: 2)
    result = compose_deadline_marks(base=base, theme_tokens=tokens,
        deadlines=(ReviewDeadline("owner", date(2026, 1, 5), date(2026, 1, 6).toordinal(), date(2026, 1, 9).toordinal(), True, 3, "3 days late"),),
        marks=(host,), window=(date(2026, 1, 1), date(2026, 1, 11)), paint_order_base=100)
    anchor, = result.captions
    assert anchor.stroke_margin == 6 and anchor.subjects == (subject,)
    ground = next(shape for shape in result.shapes if shape.placement_id == "deadline-run:owner:outline")
    assert float(ground.bounds.inline + ground.bounds.inline_size) == anchor.run_end + anchor.stroke_margin
