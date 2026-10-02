"""A Theme-declared hand-wobble completes into a deterministic perturbed outline (#588).

Synthetic geometry and Themes only: nothing here reads `examples/`. The pinned constants are the
cross-platform check: the three-OS CI computes the same integers, doubles and digests.
"""
from __future__ import annotations

from hashlib import sha256
from math import sqrt

import pytest

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.capabilities import theme_role_property_consumer
from chrona.presentation.scene.paint import PaintFamily, ScenePaintError, resolve_scene_paint
from chrona.presentation.scene.stroke_wobble import (
    MAX_OUTLINE_POINTS, WobbleLimitError, complete_path_wobble, complete_rect_wobble, fnv1a64,
    lattice_value, mix, path_polylines, rect_vertices, stream_key,
)
from chrona.presentation.scene.visual_capabilities import BASELINE_PROFILE, SVG_PROFILE, resolve_visual_profile

BOX = (100.0, 50.0, 200.0, 24.0)


def _rect(identity="bar:a", *, radius=3.0, amplitude=1.6, wavelength=22.0, seed=7, bounds=BOX):
    return complete_rect_wobble(identity, bounds, radius, amplitude=amplitude, wavelength=wavelength, seed=seed)


def _line(identity="dep:1", *, amplitude=2.0, wavelength=30.0, seed=3):
    commands = (PathCommand("move", ((10.0, 10.0),)), PathCommand("line", ((300.0, 10.0),)))
    return complete_path_wobble(identity, commands, (), amplitude=amplitude, wavelength=wavelength, seed=seed)


def _distance_to(polygon, point, *, closed):
    best = float("inf")
    for index in range(len(polygon) if closed else len(polygon) - 1):
        (ax, ay), (bx, by) = polygon[index], polygon[(index + 1) % len(polygon)]
        dx, dy = bx - ax, by - ay
        length_squared = dx * dx + dy * dy
        fraction = 0.0 if length_squared == 0 else max(0.0, min(1.0, ((point[0] - ax) * dx + (point[1] - ay) * dy) / length_squared))
        best = min(best, sqrt((point[0] - ax - fraction * dx) ** 2 + (point[1] - ay - fraction * dy) ** 2))
    return best


def test_the_generator_is_pinned_so_every_platform_computes_the_same_integers_and_doubles() -> None:
    assert mix(0) == 16294208416658607535 and mix(1) == 10451216379200822465  # the splitmix64 reference outputs
    assert fnv1a64(b"") == 0xCBF29CE484222325 and fnv1a64(b"a") == 0xAF63DC4C8601EC8C  # the FNV-1a reference vectors
    stream = stream_key(7, "bar:a")
    assert stream == 17668698437251059205
    assert [lattice_value(stream, index) for index in range(3)] == [0.17482421394393666, -0.6973662403271754, -0.6194817135349746]
    assert all(-1.0 <= lattice_value(stream, index) < 1.0 for index in range(500))


def test_a_fixed_outline_has_a_pinned_digest() -> None:
    rect = _rect()
    commands = (PathCommand("move", ((10.0, 10.0),)), PathCommand("line", ((300.0, 10.0),)),
                PathCommand("quadratic", ((400.0, 10.0), (400.0, 100.0))))
    path = complete_path_wobble("dep:1", commands, (), amplitude=2.0, wavelength=30.0, seed=3)

    assert len(rect[0]) == 96 and sha256(repr(rect).encode()).hexdigest() == "5c41312a29fbb98fbe27bb68037c8cce5f6712b7c2ba2c9bfa75f49738f1fa73"
    assert len(path[0]) == 63 and sha256(repr(path).encode()).hexdigest() == "fbb6aac1623329dafa3ed8e2c92972db1de2273e5c8ee1d806529e5bef0b4897"


def test_the_same_declaration_and_identity_give_the_same_outline_and_a_changed_input_changes_it() -> None:
    assert _rect() == _rect()
    assert _rect("bar:b") != _rect()          # each primitive has its own line
    assert _rect(seed=8) != _rect()           # the declared seed selects the family
    assert _rect(amplitude=1.0) != _rect()
    assert _rect(wavelength=30.0) != _rect()


def test_every_outline_point_stays_within_the_declared_amplitude_of_the_nominal_outline() -> None:
    nominal = rect_vertices(BOX, 3.0)
    for point in _rect(amplitude=1.6)[0]:
        assert _distance_to(nominal, point, closed=True) <= 1.6 + 0.002


def test_a_thin_rect_limits_the_amplitude_to_a_quarter_of_its_short_side() -> None:
    thin = (0.0, 0.0, 120.0, 4.0)
    nominal = rect_vertices(thin, None)

    assert max(_distance_to(nominal, point, closed=True) for point in _rect(radius=None, amplitude=8.0, bounds=thin)[0]) <= 1.0 + 0.002
    assert max(_distance_to(nominal, point, closed=True) for point in _rect(radius=None, amplitude=8.0, bounds=thin)[0]) > 0.3


def test_the_ink_stays_within_the_bounds_grown_by_the_amplitude() -> None:
    xs = [point[0] for point in _rect(radius=None)[0]]
    ys = [point[1] for point in _rect(radius=None)[0]]

    assert min(xs) >= BOX[0] - 1.6 - 0.002 and max(xs) <= BOX[0] + BOX[2] + 1.6 + 0.002
    assert min(ys) >= BOX[1] - 1.6 - 0.002 and max(ys) <= BOX[1] + BOX[3] + 1.6 + 0.002
    assert min(xs) < BOX[0] or max(xs) > BOX[0] + BOX[2] or min(ys) < BOX[1] or max(ys) > BOX[1] + BOX[3]


def test_a_closed_outline_closes_without_a_seam() -> None:
    outline = _rect(radius=None)[0]
    cells = max(2, int((2 * (BOX[2] + BOX[3])) / 22.0 + 0.5))
    step = (2 * (BOX[2] + BOX[3])) / cells / 4.0
    gaps = [sqrt((outline[(index + 1) % len(outline)][0] - outline[index][0]) ** 2
                 + (outline[(index + 1) % len(outline)][1] - outline[index][1]) ** 2) for index in range(len(outline))]

    assert max(gaps) <= step + 2 * 1.6 + 0.01       # the wrap-around gap is as short as any other
    assert outline[0] != outline[-1]                 # the first point is not repeated


def test_corners_stay_corners_and_a_rounded_corner_is_flattened() -> None:
    assert len(rect_vertices(BOX, None)) == 4
    rounded = rect_vertices(BOX, 3.0)
    assert len(rounded) == 20          # four sides' end points and four flattened corners of four steps
    assert all(BOX[0] <= px <= BOX[0] + BOX[2] and BOX[1] <= py <= BOX[1] + BOX[3] for px, py in rounded)
    assert len(_rect(radius=None)[0]) > 4


def test_an_open_outline_keeps_both_end_points_and_tapers_towards_them() -> None:
    outline = _line()[0]

    assert outline[0] == (10.0, 10.0) and outline[-1] == (300.0, 10.0)
    peaks = [abs(point[1] - 10.0) for point in outline]
    assert max(peaks) > 0.5 and max(peaks) <= 2.0 + 0.002
    assert peaks[1] <= peaks[len(peaks) // 2] + 2.0 and peaks[1] < 2.0 * 0.5   # the first step is inside the taper


def test_a_quadratic_is_flattened_and_a_move_starts_a_sub_path_with_its_own_stream() -> None:
    commands = (PathCommand("move", ((0.0, 0.0),)), PathCommand("quadratic", ((50.0, 0.0), (50.0, 50.0))),
                PathCommand("move", ((0.0, 100.0),)), PathCommand("line", ((100.0, 100.0),)))
    polylines = path_polylines(commands, ())

    assert len(polylines) == 2 and len(polylines[0]) == 5 and polylines[0][-1] == (50.0, 50.0)
    outline = complete_path_wobble("p", commands, (), amplitude=2.0, wavelength=20.0, seed=1)
    assert len(outline) == 2 and outline[0][0] == (0.0, 0.0) and outline[1][-1] == (100.0, 100.0)


def test_points_without_commands_are_one_sub_path_and_repeated_points_are_dropped() -> None:
    assert path_polylines((), ((0.0, 0.0), (0.0, 0.0), (10.0, 0.0))) == [[(0.0, 0.0), (10.0, 0.0)]]


def test_an_outline_beyond_the_point_limit_is_refused() -> None:
    commands = (PathCommand("move", ((0.0, 0.0),)), PathCommand("line", ((40000.0, 0.0),)))

    with pytest.raises(WobbleLimitError):
        complete_path_wobble("long", commands, (), amplitude=1.0, wavelength=4.0, seed=0)
    assert MAX_OUTLINE_POINTS == 8192


# --- Theme resolution ---------------------------------------------------------------------------

WOBBLE = {"wobbleAmplitude": "amp", "wobbleWavelength": "wave", "wobbleSeed": "seed"}


def _tokens(**role) -> ThemeTokenView:
    values = {"ink": {"type": "color", "value": "#102030"}, "width": {"type": "number", "value": 2},
              "amp": {"type": "number", "value": 1.6}, "wave": {"type": "number", "value": 22},
              "seed": {"type": "number", "value": 7}, "big": {"type": "number", "value": 17},
              "short": {"type": "number", "value": 3.9}, "long": {"type": "number", "value": 1001},
              "zero": {"type": "number", "value": 0}, "half": {"type": "number", "value": 1.5},
              "negative": {"type": "number", "value": -1}, "huge": {"type": "number", "value": 4294967296},
              "must": {"type": "fidelity", "value": "required"},
              "soft": {"type": "fidelity", "value": "decorative-optional"},
              "odd": {"type": "fidelity", "value": "sometimes"}}
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": values, "roles": {"planned": {"fill": "ink", "stroke": "ink", "strokeWidth": "width", **role}},
        "metrics": {}}})


def _resolve(tokens, profile=None):
    return resolve_scene_paint(tokens, "planned", PaintFamily.SOLID, visual_profile=profile)


def test_a_role_without_wobble_properties_has_no_wobble_and_no_omission() -> None:
    result = _resolve(_tokens())

    assert result.paint.wobble is None and result.omissions == ()


def test_a_declared_wobble_keeps_its_parameters_and_defaults_to_required() -> None:
    wobble = _resolve(_tokens(**WOBBLE)).paint.wobble

    assert (wobble.amplitude, wobble.wavelength, wobble.seed, wobble.fidelity) == (1.6, 22.0, 7, "required")
    assert wobble.outline == ()          # Scene completes the outline from the primitive, not the resolver


@pytest.mark.parametrize("missing", ["wobbleAmplitude", "wobbleWavelength", "wobbleSeed"])
def test_the_three_parameters_are_declared_together_or_none(missing) -> None:
    role = {key: value for key, value in WOBBLE.items() if key != missing}

    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**role))
    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_VALUE"
    assert error.value.path == "/body/roles/planned/wobbleAmplitude"


@pytest.mark.parametrize(("override", "pointer"), [
    ({"wobbleAmplitude": "big"}, "wobbleAmplitude"), ({"wobbleAmplitude": "zero"}, "wobbleAmplitude"),
    ({"wobbleAmplitude": "negative"}, "wobbleAmplitude"),
    ({"wobbleWavelength": "short"}, "wobbleWavelength"), ({"wobbleWavelength": "long"}, "wobbleWavelength"),
    ({"wobbleSeed": "half"}, "wobbleSeed"), ({"wobbleSeed": "negative"}, "wobbleSeed"),
    ({"wobbleSeed": "huge"}, "wobbleSeed"),
])
def test_a_value_outside_its_limit_fails_at_its_own_pointer(override, pointer) -> None:
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**{**WOBBLE, **override}))

    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_LIMIT"
    assert error.value.path == f"/body/roles/planned/{pointer}"


def test_the_limits_themselves_are_admitted() -> None:
    low = _tokens(wobbleAmplitude="half", wobbleWavelength="wave", wobbleSeed="zero")

    assert _resolve(low).paint.wobble.seed == 0
    assert _resolve(_tokens(**{**WOBBLE, "wobbleFidelity": "soft"})).paint.wobble.fidelity == "decorative-optional"


def test_an_unknown_fidelity_is_refused() -> None:
    with pytest.raises((ScenePaintError, Exception)) as error:
        _resolve(_tokens(**{**WOBBLE, "wobbleFidelity": "odd"}))

    assert getattr(error.value, "diagnostic_id", None) == "E_VISUAL_CAPABILITY_FIDELITY"


def test_the_rich_profile_keeps_the_wobble_and_the_baseline_follows_the_ladder() -> None:
    rich = resolve_visual_profile(SVG_PROFILE, "svg")
    baseline = resolve_visual_profile(BASELINE_PROFILE, "svg")
    optional = _tokens(**{**WOBBLE, "wobbleFidelity": "soft"})

    assert _resolve(_tokens(**WOBBLE), rich).paint.wobble is not None
    omitted = _resolve(optional, baseline)
    assert omitted.paint.wobble is None
    assert [(item.role, item.treatment, item.visual_profile, item.paintable_profile, item.source_ref)
            for item in omitted.omissions] == [("planned", "wobble", BASELINE_PROFILE, SVG_PROFILE,
                                                "/body/roles/planned/wobbleAmplitude")]
    with pytest.raises(ScenePaintError) as error:
        _resolve(_tokens(**WOBBLE), baseline)
    assert error.value.diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED"


@pytest.mark.parametrize("role", ["planned", "actual", "network-node", "dependency", "axis-rule", "annotation-callout-leader"])
def test_the_properties_are_admitted_on_rect_and_path_roles(role) -> None:
    for name in ("wobbleAmplitude", "wobbleWavelength", "wobbleSeed", "wobbleFidelity"):
        assert theme_role_property_consumer(role, name) is not None, (role, name)


@pytest.mark.parametrize("role", ["text", "background", "canvas-texture", "icon-mark", "annotation-note-text", "group-header"])
def test_the_properties_are_refused_on_text_canvas_icon_and_texture_roles(role) -> None:
    for name in ("wobbleAmplitude", "wobbleWavelength", "wobbleSeed", "wobbleFidelity"):
        assert theme_role_property_consumer(role, name) is None, (role, name)
