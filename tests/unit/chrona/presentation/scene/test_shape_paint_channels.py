"""Completed shape channels do not erase catalogue fill pigments (#871)."""
from dataclasses import replace

import pytest

from chrona.presentation.scene.model import ScenePaint, ScenePrimitive
from chrona.presentation.scene.paint import ScenePaintError, restrict_paint_channels
from chrona.presentation.scene.serialization import _primitive
from chrona.presentation.scene.v05_builder import _complete_shape_channels


def _paint():
    return ScenePaint(fill="#FFFFFF", stroke="#123456", stroke_width=3,
                      dash=(2, 4), opacity=0.5)


def test_absent_mask_preserves_paint_identity():
    paint = _paint()
    assert restrict_paint_channels(paint, None, "period-band") is paint


def test_plain_fill_has_no_host_outline():
    paint = restrict_paint_channels(_paint(), "fill", "period-band")
    assert (paint.fill, paint.opacity) == ("#FFFFFF", 0.5)
    assert (paint.stroke, paint.stroke_width, paint.dash) == (None, None, ())


def test_pattern_fill_keeps_catalogue_ink_not_host_outline():
    paint = _paint()
    assert restrict_paint_channels(paint, "fill", "period-band",
                                  patterned_fill=True) == paint


def test_stroke_mask_preserves_line_paint_without_fill():
    paint = restrict_paint_channels(_paint(), "stroke", "period-band")
    assert paint.fill is None
    assert (paint.stroke, paint.stroke_width, paint.dash) == ("#123456", 3, (2, 4))


@pytest.mark.parametrize("channels,paint,missing", [
    ("fill", replace(_paint(), fill=None), "fill"),
    ("stroke", replace(_paint(), stroke=None), "stroke"),
    ("stroke", replace(_paint(), stroke_width=None), "strokeWidth"),
])
def test_required_channels_have_exact_role_pointer(channels, paint, missing):
    with pytest.raises(ScenePaintError) as error:
        restrict_paint_channels(paint, channels, "period-band")
    assert error.value.diagnostic_id == "E_THEME_ROLE_REQUIRED"
    assert error.value.path == f"/body/roles/period-band/{missing}"


def test_completion_consumes_transient_mask():
    primitive = ScenePrimitive("band", "Rect", "period", "period", "period-band",
                               "period-band", (0, 0, 30, 20), paint=_paint(),
                               paint_channels="fill")
    completed, omissions = _complete_shape_channels((primitive, ()))
    assert completed.paint_channels is None
    assert completed.paint.stroke is None
    assert omissions == ()
    assert _primitive(completed) == _primitive(replace(primitive, paint=completed.paint,
                                                      paint_channels=None))
    assert "paint_channels" not in _primitive(completed)
    assert "paintChannels" not in _primitive(completed)


@pytest.mark.parametrize("kind,channels", [("Text", "fill"), ("Rect", "both")])
def test_invalid_shape_mask_is_rejected(kind, channels):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive("band", kind, "period", "period", "period-band",
                       "period-band", (0, 0, 30, 20), paint_channels=channels)
