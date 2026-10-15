from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_deadlines import _outline
from chrona.presentation.layout.surface_quality import ShapePlacement
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject


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
