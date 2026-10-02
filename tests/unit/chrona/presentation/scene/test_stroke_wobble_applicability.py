"""Where a hand-wobble applies, and what refuses it (#588). Hand-built primitives; no `examples/` input."""
from __future__ import annotations

from dataclasses import replace

import pytest

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.scene.model import (
    ImageFill, ImageTile, PatternGeometry, PatternStroke, ScenePaint, ScenePrimitive, StrokeWobble, SymbolGeometry,
)
from chrona.presentation.scene.v05_builder import SceneBuildError, _complete_wobble


def _primitive(kind="Rect", **overrides) -> ScenePrimitive:
    values = {"scene_id": "mark:1", "kind": kind, "source_ref": "obj", "source_kind": "primary", "purpose": "planned",
              "visual_role": "planned", "bounds": (10.0, 10.0, 80.0, 20.0)}
    return ScenePrimitive(**{**values, **overrides})


def _paint(stroke="#000000", **overrides) -> ScenePaint:
    return ScenePaint("#FFFFFF", stroke, 1.0, (), 1.0, wobble=StrokeWobble(1.6, 22.0, 7, "required"), **overrides)


def test_a_stroked_rect_completes_a_closed_outline_and_a_path_an_open_one() -> None:
    rect = _complete_wobble(_primitive(), _paint(), False).wobble
    line = _primitive("Path", points=((0.0, 0.0), (100.0, 0.0)), bounds=(0.0, 0.0, 0.0, 0.0))
    path = _complete_wobble(line, _paint(), False).wobble

    assert rect.closed and len(rect.outline) == 1 and len(rect.outline[0]) > 4
    assert not path.closed and path.outline[0][0] == (0.0, 0.0) and path.outline[0][-1] == (100.0, 0.0)


def test_the_treatment_does_not_apply_to_what_must_keep_its_exact_geometry() -> None:
    pattern = PatternGeometry(10.0, 10.0, 45.0, (PatternStroke((0.0, 0.0), (10.0, 10.0), 1.0),))
    image = ImageFill("asset", (4, 4), b"x", (ImageTile((0.0, 0.0, 4.0, 4.0), (0.0, 0.0, 10.0, 10.0)),))
    symbol = SymbolGeometry((PathCommand("move", ((0.0, 0.0),)), PathCommand("line", ((5.0, 5.0),))))
    cases = {
        "fill only": (_primitive(), replace(_paint(), stroke=None), False),
        "pattern": (_primitive(pattern=pattern), _paint(), False),
        "image": (_primitive(), _paint(image=image), False),
        "clip host": (_primitive(), _paint(), True),
        "symbol": (_primitive("Symbol", symbol=symbol), _paint(), False),
        "text": (_primitive("Text"), _paint(), False),
    }
    for name, (primitive, paint, host) in cases.items():
        assert _complete_wobble(primitive, paint, host).wobble is None, name


def test_a_surface_keeps_the_exact_rectangle_of_a_clip_host_and_wobbles_its_other_bars() -> None:
    from chrona.presentation.model.theme_tokens import ThemeTokenView
    from chrona.presentation.scene.model import SceneSurface
    from chrona.presentation.scene.v05_builder import _complete_surface_paint

    values = {"ink": {"type": "color", "value": "#102030"}, "w": {"type": "number", "value": 2},
              "amp": {"type": "number", "value": 1.6}, "wave": {"type": "number", "value": 22},
              "seed": {"type": "number", "value": 7}}
    roles = {"planned": {"fill": "ink", "stroke": "ink", "strokeWidth": "w", "wobbleAmplitude": "amp",
                         "wobbleWavelength": "wave", "wobbleSeed": "seed"}, "background": {"fill": "ink"}}
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                             "body": {"values": values, "roles": roles, "metrics": {}}})
    host = _primitive(scene_id="host", bounds=(10.0, 10.0, 80.0, 40.0))
    child = _primitive(scene_id="child", bounds=(20.0, 20.0, 30.0, 10.0), clip_source_id="host")
    other = _primitive(scene_id="other", bounds=(10.0, 70.0, 80.0, 20.0))
    surface = SceneSurface("surface", (), (), (), None, (host, child, other), None, canvas_bounds=(0.0, 0.0, 200.0, 200.0))

    completed = {item.scene_id: item for item in _complete_surface_paint(surface, tokens, None, (200.0, 200.0)).primitives}

    assert completed["host"].paint.wobble is None           # the clip is the exact rectangle
    assert completed["child"].paint.wobble is not None and completed["other"].paint.wobble is not None


def test_the_profile_gate_refuses_a_required_wobble_directly_and_lets_an_optional_one_pass() -> None:
    from chrona.presentation.scene.model import SceneSurface
    from chrona.presentation.scene.visual_capabilities import (
        BASELINE_PROFILE, SVG_PROFILE, VisualCapabilityError, resolve_visual_profile, validate_surface_visual_profile,
    )

    def surface(fidelity):
        paint = replace(_paint(), wobble=replace(_paint().wobble, fidelity=fidelity))
        return SceneSurface("surface", (), (), (), None, (_primitive(paint=paint),), _paint(),
                            canvas_bounds=(0.0, 0.0, 200.0, 200.0))

    baseline, rich = resolve_visual_profile(BASELINE_PROFILE, "svg"), resolve_visual_profile(SVG_PROFILE, "svg")
    with pytest.raises(VisualCapabilityError) as error:
        validate_surface_visual_profile(surface("required"), baseline)
    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED"
    validate_surface_visual_profile(surface("required"), rich)


def test_each_sub_path_of_a_path_has_its_own_line() -> None:
    from chrona.presentation.scene.stroke_wobble import complete_path_wobble as complete

    commands = (PathCommand("move", ((0.0, 0.0),)), PathCommand("line", ((200.0, 0.0),)),
                PathCommand("move", ((0.0, 50.0),)), PathCommand("line", ((200.0, 50.0),)))
    first, second = complete("p", commands, (), amplitude=2.0, wavelength=20.0, seed=1)

    assert [round(py, 3) for _, py in first] != [round(py - 50.0, 3) for _, py in second]


def test_a_closed_outline_over_the_point_limit_is_refused_and_so_is_the_sum_of_sub_paths() -> None:
    from chrona.presentation.scene.stroke_wobble import WobbleLimitError, complete_path_wobble, complete_rect_wobble

    with pytest.raises(WobbleLimitError):
        complete_rect_wobble("big", (0.0, 0.0, 20000.0, 20000.0), None, amplitude=1.0, wavelength=30.0, seed=0)
    commands = ((PathCommand("move", ((0.0, 0.0),)), PathCommand("line", ((5000.0, 0.0),)))
                + (PathCommand("move", ((0.0, 50.0),)), PathCommand("line", ((5000.0, 50.0),))) * 2)
    with pytest.raises(WobbleLimitError):
        complete_path_wobble("sum", commands, (), amplitude=1.0, wavelength=6.0, seed=0)


def test_an_outline_over_the_point_limit_is_a_limit_failure_at_the_wavelength_pointer() -> None:
    long_path = _primitive("Path", points=((0.0, 0.0), (40000.0, 0.0)), bounds=(0.0, 0.0, 0.0, 0.0))
    paint = _paint()
    paint = replace(paint, wobble=replace(paint.wobble, wavelength=4.0))

    with pytest.raises(SceneBuildError) as error:
        _complete_wobble(long_path, paint, False)
    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_LIMIT"
    assert error.value.path == "/body/roles/planned/wobbleWavelength"
