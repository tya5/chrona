from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.legend_diagnostics import _shape_signature, completed_legend_diagnostics
from chrona.presentation.layout.mark_geometry import complete_point_outline, symbol_parts
from chrona.presentation.layout.surface_legend import _completed_point_key_parts
from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.color_separability import ScaleCollision
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_paint import (
    GradientPaintIntent, PaintFamily, ThemePaintError, ThemePaintInputs, ThemePaintWitness,
)
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.theme_tokens import ThemeTokenView


def _paint(*, fill="#176B87", stroke=None, width=None, dash=(), opacity=Decimal(1), gradient=None):
    channels = ThemePaintInputs(fill, stroke, width, dash, opacity, False)
    return ThemePaintWitness(channels, channels, PaintFamily.SOLID, None, gradient)


def _entry(role, key, label, *, pattern_identity=None):
    realized = RealizedLegendKey(role, role, key, pattern_identity=pattern_identity, base_label=label)
    return SurfaceLegendEntry(role, label, realized_key=realized)


def _batch(entries, figures, contents=None, request=None):
    marks, shapes, relations, text = [], [], [], []
    contents = contents or {entry.source_identity: entry.label for entry in entries}
    for entry, figure in zip(entries, figures):
        if figure[0] == "mark":
            _, bounds, parts, paints = figure
            marks.append(SimpleNamespace(source_ref=entry.source_identity, bounds=bounds,
                symbol_parts=parts, legend_paints=paints, mark_shape="point", corner_radius=0))
        elif figure[0] == "shape":
            _, bounds, shape_kind, paint, swatch_shape, *path_commands = figure
            shapes.append(SimpleNamespace(source_ref=entry.source_identity, bounds=bounds,
                kind=shape_kind, legend_paint=paint, legend_swatch_shape=swatch_shape,
                visual_role=entry.role, path_commands=path_commands[0] if path_commands else (),
                points=(), corner_radius=0, paint_channels=None))
        else:
            _, relation = figure
            relations.append(relation)
        text.append(SimpleNamespace(placement_id=entry.text_placement_id,
                                    content=contents[entry.source_identity], overflow="fit"))
    request = request or SimpleNamespace(theme_tokens=None, paint_capabilities=None,
        surface_content=SimpleNamespace(scale_legend_paints=()))
    return completed_legend_diagnostics(request, entries, marks, shapes, relations, text)


def _box(x, y, width, height):
    return SimpleNamespace(inline=x, block=y, inline_size=width, block_size=height)


def _theme_request(*, scale_paints=(), different_line=False):
    theme = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"planned-fill": {"type": "color", "value": "#176B87"},
                             "actual-fill": {"type": "color", "value": "#176B87"},
                             "planned-stroke": {"type": "color", "value": "#172033"},
                             "actual-stroke": {"type": "color", "value": "#172033"},
                             "deadline-stroke": {"type": "color", "value": "#B91C1C"},
                             "width": {"type": "number", "value": 2}},
                 "roles": {"planned": {"fill": "planned-fill", "stroke": "planned-stroke",
                                        "strokeWidth": "width"},
                           "actual": {"fill": "actual-fill", "stroke": "actual-stroke",
                                       "strokeWidth": "width"},
                           "dependency": {"stroke": "planned-stroke", "strokeWidth": "width"},
                           "deadline-mark": {"stroke": "deadline-stroke" if different_line else "actual-stroke",
                                             "strokeWidth": "width"}},
                 "catalogAssets": {}},
    })
    return SimpleNamespace(theme_tokens=theme, paint_capabilities=PaintWitnessCapabilities(),
        surface_content=SimpleNamespace(scale_legend_paints=scale_paints))


def test_figure_comparison_ignores_translation_and_footprint_but_keeps_finite_shapes_and_ink():
    same = _paint()
    left, right = _entry("planned", same, "Work"), _entry("actual", same, "Observed")
    signature = lambda entry, shape: (entry, ("shape", _box(0, 0, 20, 10), "Rect", same, shape))

    # Unit-box normalization suppresses a false difference from allocation position/size.
    collision = _batch((left, right), (
        signature(left, None)[1],
        ("shape", _box(100, 40, 40, 20), "Rect", same, None),
    ))
    assert "W_LEGEND_SWATCH_COLLISION" in collision[0]

    circle_vs_pair = _batch((left, right), (
        ("shape", _box(0, 0, 20, 10), "Symbol", same, "circle"),
        ("shape", _box(100, 40, 40, 20), "Path", same, "rule-pair"),
    ), request=_theme_request())
    assert "W_LEGEND_SWATCH_COLLISION" not in circle_vs_pair[0]

    different_stroke = _paint(stroke="#172033", width=Decimal(2), opacity=Decimal("0.5"))
    right_stroke = _entry("actual", different_stroke, "Observed")
    changed_ink = _batch((left, right_stroke), (
        ("shape", _box(0, 0, 20, 10), "Rect", same, None),
        ("shape", _box(100, 40, 40, 20), "Rect", different_stroke, None),
    ))
    assert "W_LEGEND_SWATCH_COLLISION" not in changed_ink[0]


def test_shape_channel_restriction_removes_unused_paint_from_collision_identity():
    left_paint = _paint(fill="#176B87", stroke="#172033", width=Decimal(2))
    right_paint = _paint(fill="#D99024", stroke="#172033", width=Decimal(2))
    left, right = _entry("planned", left_paint, "Work"), _entry("actual", right_paint, "Observed")
    def shape(entry, paint, x):
        return SimpleNamespace(source_ref=entry.source_identity, bounds=_box(x, 0, 20, 10),
            kind="Path", legend_paint=paint, legend_swatch_shape=None, visual_role=entry.role,
            path_commands=(), points=(), corner_radius=0, paint_channels="stroke")
    result = completed_legend_diagnostics(SimpleNamespace(theme_tokens=None, paint_capabilities=None,
        surface_content=SimpleNamespace(scale_legend_paints=())), (left, right), (),
        (shape(left, left_paint, 0), shape(right, right_paint, 50)), (),
        (SimpleNamespace(placement_id=left.text_placement_id, content="Work", overflow="fit"),
         SimpleNamespace(placement_id=right.text_placement_id, content="Observed", overflow="fit")))
    assert "W_LEGEND_SWATCH_COLLISION" in result[0]


@pytest.mark.parametrize("channels", ("stroke", None))
def test_stroke_only_path_shape_does_not_require_unused_fill_channel(channels):
    theme = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"band-stroke": {"type": "color", "value": "#172033"},
                             "width": {"type": "number", "value": 1}},
                 "roles": {"period-band": {"stroke": "band-stroke", "strokeWidth": "width"}},
                 "catalogAssets": {}},
    })
    request = SimpleNamespace(theme_tokens=theme, paint_capabilities=PaintWitnessCapabilities(),
                               surface_content=SimpleNamespace(scale_legend_paints=()))
    entry = SurfaceLegendEntry("period-band", "Launch", source_ref="period:launch")
    shape = SimpleNamespace(source_ref=entry.source_identity, bounds=_box(0, 0, 20, 10),
        kind="Path", legend_paint=None, legend_swatch_shape=None, visual_role="period-band",
        path_commands=(), points=((0, 5), (20, 5)), corner_radius=0, paint_channels=channels)
    text = SimpleNamespace(placement_id=entry.text_placement_id, content="Launch", overflow="fit")

    diagnostics, _ = completed_legend_diagnostics(request, (entry,), (), (shape,), (), (text,))

    assert diagnostics == ()


def test_fill_only_path_uses_solid_family_and_fill_geometry_mode():
    theme = ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
        "body": {"values": {"band-fill": {"type": "color", "value": "#176B87"}},
                 "roles": {"period-band": {"fill": "band-fill"}},
                 "catalogAssets": {}},
    })
    request = SimpleNamespace(theme_tokens=theme, paint_capabilities=PaintWitnessCapabilities(),
                               surface_content=SimpleNamespace(scale_legend_paints=()))
    entry = SurfaceLegendEntry("period-band", "Launch", source_ref="period:launch")
    shape = SimpleNamespace(source_ref=entry.source_identity, bounds=_box(0, 0, 20, 10),
        kind="Path", legend_paint=None, legend_swatch_shape=None, visual_role="period-band",
        path_commands=(), points=((0, 5), (20, 5)), corner_radius=0, paint_channels="fill")

    signature = _shape_signature(request, entry, shape)

    assert signature[0][0][0] == "fill"
    assert signature[1][0][0] == ("solid", "#176B87")
    assert signature[1][0][1:4] == (None, None, ())


def test_finite_circle_and_completed_circle_glyph_share_same_figure_identity():
    paint = _paint()
    finite_entry = _entry("planned", paint, "Planned")
    glyph_entry = _entry("actual", paint, "Observed")
    shape_part = symbol_parts({"shape": "circle"}, (0, 0, 10, 10))[0]
    mark_part = symbol_parts({"shape": "circle"}, (40, 30, 20, 20))[0]
    commands = shape_part.commands
    part = SimpleNamespace(paint_mode="fill", line_cap=None, line_join=None, commands=mark_part.commands)
    request = _theme_request()
    result = completed_legend_diagnostics(request, (finite_entry, glyph_entry),
        (SimpleNamespace(source_ref=glyph_entry.source_identity, bounds=_box(40, 30, 20, 20),
            symbol_parts=(part,), legend_paints=(paint,), mark_shape="point", corner_radius=0),),
        (SimpleNamespace(source_ref=finite_entry.source_identity, bounds=_box(0, 0, 10, 10),
            kind="Symbol", legend_paint=paint, legend_swatch_shape="circle", visual_role="planned",
            path_commands=commands, points=(), corner_radius=0, paint_channels=None),), (),
        (SimpleNamespace(placement_id=finite_entry.text_placement_id, content="Planned", overflow="fit"),
         SimpleNamespace(placement_id=glyph_entry.text_placement_id, content="Observed", overflow="fit")))
    assert "W_LEGEND_SWATCH_COLLISION" in result[0]


def test_scale_key_figure_uses_closed_value_fill_overrides():
    left = SurfaceLegendEntry("scale:owner", "A", source_ref="scale:owner:a")
    right = SurfaceLegendEntry("scale:owner", "B", source_ref="scale:owner:b")
    figures = (
        ("shape", _box(0, 0, 10, 10), "Rect", None, None),
        ("shape", _box(20, 30, 20, 20), "Rect", None, None),
    )
    different = _batch((left, right), figures,
        request=_theme_request(scale_paints=((left.source_identity, "#176B87"),
                                             (right.source_identity, "#D99024"))))
    assert "W_LEGEND_SWATCH_COLLISION" not in different[0]
    equal = _batch((left, right), figures,
        request=_theme_request(scale_paints=((left.source_identity, "#176B87"),
                                             (right.source_identity, "#176B87"))))
    assert "W_LEGEND_SWATCH_COLLISION" in equal[0]


def test_multipart_figure_compares_ordered_completed_geometry_and_paint():
    first, second = _paint(fill="#176B87"), _paint(fill="#D99024")
    left, right = _entry("actual", first, "Observed"), _entry("snapshot", first, "Baseline")
    def part(mode, x, y):
        return SimpleNamespace(paint_mode=mode, line_cap="round", line_join="round",
            commands=(PathCommand("move", ((x, y + 5),)), PathCommand("line", ((x + 10, y),))))
    part_a, part_b = part("fill", 0, 0), part("stroke", 0, 0)
    other_a = SimpleNamespace(paint_mode="fill", line_cap="round", line_join="round",
        commands=(PathCommand("move", ((20, 40),)), PathCommand("line", ((40, 30),))))
    other_b = SimpleNamespace(paint_mode="stroke", line_cap="round", line_join="round",
        commands=(PathCommand("move", ((20, 40),)), PathCommand("line", ((40, 30),))))
    equal = _batch((left, right), (
        ("mark", _box(0, 0, 10, 10), (part_a, part_b), (first, second)),
        ("mark", _box(20, 30, 20, 20), (other_a, other_b), (first, second)),
    ))
    assert "W_LEGEND_SWATCH_COLLISION" in equal[0]
    reversed_parts = _batch((left, right), (
        ("mark", _box(0, 0, 10, 10), (part_a, part_b), (first, second)),
        ("mark", _box(20, 30, 20, 20), (other_b, other_a), (second, first)),
    ))
    assert "W_LEGEND_SWATCH_COLLISION" not in reversed_parts[0]


def test_canonical_legend_geometry_identity_ignores_fractional_translation_and_footprint():
    paint = _paint(fill="#101828", stroke="#101828", width=Decimal(1))
    left, right = _entry("actual", paint, "Actual"), _entry("milestone", paint, "Gate")
    canonical = (("fill", None, None, (
        ("move", ((0.0, 0.0),)), ("line", ((1.0, 0.0),)),
        ("line", ((1.0, 1.0),)), ("line", ((0.0, 1.0),)),
        ("line", ((0.0, 0.0),)),
    )),)

    def mark(entry, bounds, raw_path, mark_paint=paint):
        part = SimpleNamespace(paint_mode="fill", line_cap=None, line_join=None,
                               commands=(PathCommand("move", ((raw_path, raw_path),)),
                                         PathCommand("line", ((raw_path + 4, raw_path + 4),))))
        return SimpleNamespace(source_ref=entry.source_identity, bounds=bounds,
            symbol_parts=(part,), legend_paints=(mark_paint,), legend_geometry_identity=canonical,
            mark_shape="point", corner_radius=0)

    result = completed_legend_diagnostics(
        _theme_request(), (left, right),
        (mark(left, _box(10.25, 20.75, 8.0, 8.0), 10.25),
         mark(right, _box(100.125, 40.875, 20.0, 20.0), 100.125)),
        (), (),
        (SimpleNamespace(placement_id=left.text_placement_id, content="Actual", overflow="fit"),
         SimpleNamespace(placement_id=right.text_placement_id, content="Gate", overflow="fit")))

    assert "W_LEGEND_SWATCH_COLLISION" in result[0]

    # A faithful ink difference still prevents a collision even with the same
    # canonical completed geometry witness.
    different = _paint(fill="#D99024", stroke="#D99024", width=Decimal(1))
    different_right = _entry("milestone", different, "Gate")
    changed = completed_legend_diagnostics(
        _theme_request(), (left, different_right),
        (mark(left, _box(10.25, 20.75, 8.0, 8.0), 10.25),
         mark(different_right, _box(100.125, 40.875, 20.0, 20.0), 100.125, different)),
        (), (),
        (SimpleNamespace(placement_id=left.text_placement_id, content="Actual", overflow="fit"),
         SimpleNamespace(placement_id=right.text_placement_id, content="Gate", overflow="fit")))
    assert "W_LEGEND_SWATCH_COLLISION" not in changed[0]

    # Before the canonical witness, these unrelated placed coordinates do not
    # normalize to one figure; this guards the regression the witness fixes.
    def without_canonical(entry, bounds, raw_path, mark_paint):
        candidate = mark(entry, bounds, raw_path, mark_paint)
        candidate.legend_geometry_identity = None
        return candidate
    legacy = completed_legend_diagnostics(
        _theme_request(), (left, right),
        (without_canonical(left, _box(10.25, 20.75, 8.0, 8.0), 10.25, paint),
         without_canonical(right, _box(100.125, 40.875, 20.0, 20.0), 100.125, paint)),
        (), (),
        (SimpleNamespace(placement_id=left.text_placement_id, content="Actual", overflow="fit"),
         SimpleNamespace(placement_id=right.text_placement_id, content="Gate", overflow="fit")))
    assert "W_LEGEND_SWATCH_COLLISION" not in legacy[0]


def test_completed_point_legend_witness_preserves_placed_parts_exactly():
    theme = _theme_request().theme_tokens
    token = {"shape": "circle"}
    first_bounds = (10.25, 20.75, 8.0, 8.0)
    second_bounds = (100.125, 40.875, 20.0, 20.0)

    first_parts, first_identity = _completed_point_key_parts(token, first_bounds, "actual", theme)
    second_parts, second_identity = _completed_point_key_parts(token, second_bounds, "actual", theme)
    for bounds, completed in ((first_bounds, first_parts), (second_bounds, second_parts)):
        before_change = complete_point_outline(
            symbol_parts(token, bounds, catalog_glyphs=theme.catalog_glyphs),
            paint_role="actual", theme_tokens=theme)
        assert completed == before_change
    assert first_identity == second_identity


def test_omitted_gradient_has_solid_identity_and_duplicate_uses_final_text():
    omitted = GradientPaintIntent("#FFFFFF", "#000000", Decimal(90), "decorative-optional", False)
    solid, no_omission = _paint(gradient=omitted), _paint()
    left, right = _entry("actual", solid, "Actual"), _entry("planned", no_omission, "Planned")
    result = _batch((left, right), (
        ("shape", _box(0, 0, 10, 10), "Rect", solid, None),
        ("shape", _box(50, 50, 30, 30), "Rect", no_omission, None),
    ), contents={left.source_identity: "Shared…", right.source_identity: "Shared…"})
    assert "W_LEGEND_SWATCH_COLLISION" in result[0]
    assert "W_LEGEND_LABEL_DUPLICATE" in result[0]
    warning = result[1][result[0].index("W_LEGEND_LABEL_DUPLICATE")]
    assert warning.subjects == (
        DiagnosticSubject(f"legend-key:{left.realized_key.key_id}", "Actual (actual)"),
        DiagnosticSubject(f"legend-key:{right.realized_key.key_id}", "Planned (planned)"),
    )


def test_unemitted_pattern_declaration_does_not_distinguish_keys():
    declared_only = ThemePaintWitness(
        _paint().channels, _paint().effective_channels, PaintFamily.SOLID,
        (("kind", ("catalog",)), ("asset", ("unused-pattern",))), None)
    left = _entry("actual", declared_only, "Actual")
    right = _entry("planned", _paint(), "Planned")
    # The closed key witness says no pattern was emitted. Raw Theme declarations
    # are deliberately not copied into RealizedLegendKey.pattern_identity.
    result = _batch((left, right), (
        ("shape", _box(0, 0, 10, 10), "Rect", declared_only, None),
        ("shape", _box(20, 30, 20, 20), "Rect", _paint(), None),
    ))
    assert "W_LEGEND_SWATCH_COLLISION" in result[0]
    admitted = _entry("actual", declared_only, "Actual",
                      pattern_identity=("catalog", 8, 8, 0, 5000, (("circle",),)))
    patterned = _batch((admitted, right), (
        ("shape", _box(0, 0, 10, 10), "Rect", declared_only, None),
        ("shape", _box(20, 30, 20, 20), "Rect", _paint(), None),
    ))
    assert "W_LEGEND_SWATCH_COLLISION" not in patterned[0]


def test_line_marker_difference_and_filtered_label_are_not_reported():
    paint = _paint(stroke="#176B87", fill=None, width=Decimal(2))
    left, right = _entry("dependency", paint, "Link"), _entry("deadlineMark", paint, "Deadline")
    def relation(entry, marker):
        return SimpleNamespace(relation_id=entry.swatch_placement_id, suppressed=False,
            semantic_id=entry.role, points=((0, 5), (10, 5)), path_commands=(),
            marker_start=None, marker_end=marker)
    request = SimpleNamespace(theme_tokens=None, paint_capabilities=None, surface_content=None)
    text = [SimpleNamespace(placement_id=entry.text_placement_id, content=entry.label, overflow="fit")
            for entry in (left, right)]
    # Different terminal shapes are different figures even with the same line ink.
    result = completed_legend_diagnostics(request, (left, right), (), (),
        (relation(left, None), relation(right, "triangle")), text)
    assert "W_LEGEND_SWATCH_COLLISION" not in result[0]

    # A final candidate missing its label is filtered and cannot form a warning pair.
    result = completed_legend_diagnostics(request, (left, right), (), (),
        (relation(left, None), relation(right, None)), text[:1])
    assert result == ((), ())


def test_line_keys_use_canonical_theme_roles_and_full_completed_stroke():
    left = SurfaceLegendEntry("dependency", "Dependency")
    right = SurfaceLegendEntry("deadlineMark", "Deadline")
    def relation(entry):
        return SimpleNamespace(relation_id=entry.swatch_placement_id, suppressed=False,
            semantic_id=entry.role, points=((0, 5), (10, 5)), path_commands=(),
            marker_start=None, marker_end=None)
    text = [SimpleNamespace(placement_id=entry.text_placement_id, content=entry.label, overflow="fit")
            for entry in (left, right)]
    equal_ink = completed_legend_diagnostics(_theme_request(), (left, right), (), (),
        (relation(left), relation(right)), text)
    assert "W_LEGEND_SWATCH_COLLISION" in equal_ink[0]
    different_ink = completed_legend_diagnostics(_theme_request(different_line=True), (left, right), (), (),
        (relation(left), relation(right)), text)
    assert "W_LEGEND_SWATCH_COLLISION" not in different_ink[0]


@pytest.mark.parametrize("different_fill", [False, True])
def test_catalogue_key_uses_intrinsic_pattern_width_not_an_unused_host_width(different_fill):
    request = _theme_request()
    theme = deepcopy(request.theme_tokens.resolved_theme)
    body = theme["body"]
    body["values"]["dots"] = {"type": "pattern", "value": {"kind": "catalog", "ref": "dots"}}
    for role in ("planned", "actual"):
        body["roles"][role].pop("strokeWidth")
        body["roles"][role]["pattern"] = "dots"
    if different_fill:
        body["values"]["actual-fill"]["value"] = "#D99024"
    request.theme_tokens = ThemeTokenView(theme, catalog_patterns={"dots": {
        "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
        "densityBasisPoints": 1000,
        "primitives": [{"kind": "circle", "cx": 4, "cy": 4, "radius": 1}],
    }})
    left, right = SurfaceLegendEntry("planned", "Work"), SurfaceLegendEntry("actual", "Observed")
    result = _batch((left, right), (
        ("shape", _box(0, 0, 10, 10), "Rect", None, None),
        ("shape", _box(20, 30, 20, 20), "Rect", None, None),
    ), request=request)
    assert ("W_LEGEND_SWATCH_COLLISION" in result[0]) is not different_fill


def test_ordinary_key_still_requires_its_declared_stroke_width():
    request = _theme_request()
    theme = deepcopy(request.theme_tokens.resolved_theme)
    theme["body"]["roles"]["planned"].pop("strokeWidth")
    request.theme_tokens = ThemeTokenView(theme)
    entry = SurfaceLegendEntry("planned", "Work")
    with pytest.raises(ThemePaintError) as error:
        _batch((entry,), (("shape", _box(0, 0, 10, 10), "Rect", None, None),), request=request)
    assert error.value.diagnostic_id == "E_THEME_ROLE_REQUIRED"
    assert error.value.path == "/body/roles/planned/strokeWidth"


def test_completed_encoded_pair_warning_uses_typed_scale_and_final_visible_figures():
    blue = _paint(fill="#0000FF")
    near_blue = _paint(fill="#0000FE")
    duplicate_facts = tuple(ScaleCollision("risk", "high", "medium", vision, 0.0)
                            for vision in ("normal", "protanopia", "deuteranopia", "tritanopia", "grayscale"))
    encoded = SurfaceLegendEntry("scale:risk:high", "High", view_scale_id="risk",
        view_scale_domain_value="high",
        scale_collisions=duplicate_facts)
    semantic = SurfaceLegendEntry("semantic:milestone", "Milestone")
    request = _theme_request()

    visible = _batch((encoded, semantic), (
        ("shape", _box(0, 0, 10, 10), "Rect", blue, None),
        ("shape", _box(20, 30, 20, 20), "Rect", near_blue, None),
    ), request=request)
    assert "W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.127" in visible[0]

    # Same-scale values remain the scale domain's responsibility.
    same_scale = SurfaceLegendEntry("scale:risk:medium", "Medium", view_scale_id="risk",
        view_scale_domain_value="medium", scale_collisions=encoded.scale_collisions)
    same_scale_result = _batch((encoded, same_scale), (
        ("shape", _box(0, 0, 10, 10), "Rect", blue, None),
        ("shape", _box(20, 30, 20, 20), "Rect", blue, None),
    ), request=request)
    assert not any(item.startswith("W_LEGEND_COLOR_NOT_SEPARABLE:") for item in same_scale_result[0])

    # A suppressed/missing final text candidate is excluded even when its figure exists.
    marks, shapes, relations, _text = [], [], [], []
    shapes = [
        SimpleNamespace(source_ref=encoded.source_identity, bounds=_box(0, 0, 10, 10),
            kind="Rect", legend_paint=blue, legend_swatch_shape=None, visual_role=encoded.role,
            path_commands=(), points=(), corner_radius=0, paint_channels=None),
        SimpleNamespace(source_ref=semantic.source_identity, bounds=_box(20, 30, 20, 20),
            kind="Rect", legend_paint=near_blue, legend_swatch_shape=None, visual_role=semantic.role,
            path_commands=(), points=(), corner_radius=0, paint_channels=None),
    ]
    texts = (SimpleNamespace(placement_id=encoded.text_placement_id, content="High", overflow="fit"),
             SimpleNamespace(placement_id=semantic.text_placement_id, content="Milestone", overflow="suppressed"))
    hidden = completed_legend_diagnostics(request, (encoded, semantic), marks, shapes, relations, texts)
    assert hidden == ((), ())

    # A present label without a completed swatch figure is likewise not compared.
    absent_figure = completed_legend_diagnostics(request, (encoded, semantic), marks[:0], shapes[:1], (),
        (texts[0], SimpleNamespace(placement_id=semantic.text_placement_id,
                                   content="Milestone", overflow="fit")))
    assert not any(item.startswith("W_LEGEND_COLOR_NOT_SEPARABLE:") for item in absent_figure[0])


def _theme_request_with_claimed_visions():
    request = _theme_request()
    theme = deepcopy(request.theme_tokens.resolved_theme)
    theme["body"]["colorVision"] = ["protanopia", "deuteranopia", "tritanopia"]
    request.theme_tokens = ThemeTokenView(theme)
    return request


def test_completed_ordinary_keys_warn_for_low_separation_under_cvd_without_a_claim():
    planned = _entry("planned", _paint(fill="#8957E5"), "Planned finish")
    nonworking = _entry("nonworking", _paint(fill="#2F81F7"), "Non-working day")
    request = _theme_request()

    diagnostics, provenance = _batch((planned, nonworking), (
        ("shape", _box(0, 0, 10, 10), "Rect", planned.realized_key.paint, None),
        ("shape", _box(20, 30, 20, 20), "Rect", nonworking.realized_key.paint, None),
    ), request=request)

    assert diagnostics == ("W_LEGEND_COLOR_NOT_SEPARABLE:deuteranopia:3.699",)
    assert provenance[0].subjects == (
        DiagnosticSubject(f"legend-key:{planned.realized_key.key_id}", "Planned finish (planned)"),
        DiagnosticSubject(f"legend-key:{nonworking.realized_key.key_id}", "Non-working day (nonworking)"),
    )
    assert provenance[0].color_pair.vision == "deuteranopia"
    assert provenance[0].color_pair.delta_e == pytest.approx(3.6987178254387363)

    hidden_text = (
        SimpleNamespace(placement_id=planned.text_placement_id, content="Planned finish", overflow="fit"),
        SimpleNamespace(placement_id=nonworking.text_placement_id, content="Non-working day", overflow="suppressed"),
    )
    hidden = completed_legend_diagnostics(request, (planned, nonworking), (), (
        SimpleNamespace(source_ref=planned.source_identity, bounds=_box(0, 0, 10, 10),
            kind="Rect", legend_paint=planned.realized_key.paint, legend_swatch_shape=None,
            visual_role=planned.role, path_commands=(), points=(), corner_radius=0, paint_channels=None),
        SimpleNamespace(source_ref=nonworking.source_identity, bounds=_box(20, 30, 20, 20),
            kind="Rect", legend_paint=nonworking.realized_key.paint, legend_swatch_shape=None,
            visual_role=nonworking.role, path_commands=(), points=(), corner_radius=0, paint_channels=None),
    ), (), hidden_text)
    assert hidden == ((), ())


def test_completed_identical_ordinary_keys_with_distinct_meanings_warn_in_all_modes_and_keep_final_filter():
    paint = _paint(fill="#DDD9CF")
    planned = _entry("planned", paint, "Planned finish")
    today = _entry("today", paint, "Today")
    request = _theme_request()
    result = _batch((planned, today), (
        ("shape", _box(0, 0, 10, 10), "Rect", paint, None),
        ("shape", _box(20, 30, 20, 20), "Rect", paint, None),
    ), request=request)
    assert "W_LEGEND_SWATCH_COLLISION" in result[0]
    assert {
        item for item in result[0]
        if item.startswith("W_LEGEND_COLOR_NOT_SEPARABLE:")
    } == {
        "W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.0",
        "W_LEGEND_COLOR_NOT_SEPARABLE:protanopia:0.0",
        "W_LEGEND_COLOR_NOT_SEPARABLE:deuteranopia:0.0",
        "W_LEGEND_COLOR_NOT_SEPARABLE:tritanopia:0.0",
        "W_LEGEND_COLOR_NOT_SEPARABLE:grayscale:0.0",
    }

    text = tuple(SimpleNamespace(placement_id=entry.text_placement_id,
                                 content=entry.label, overflow="fit")
                 for entry in (planned, today))
    hidden = replace(planned, swatch_visible=False)
    filtered = completed_legend_diagnostics(
        request, (hidden, today), (), (), (), text,
    )
    assert filtered == ((), ())


def test_completed_encoded_warning_does_not_replace_swatch_collision_warning():
    paint = _paint(fill="#0000FF")
    encoded = SurfaceLegendEntry("scale:risk:high", "High", view_scale_id="risk",
                                 view_scale_domain_value="high")
    semantic = SurfaceLegendEntry("semantic:milestone", "Milestone")
    result = _batch((encoded, semantic), (
        ("shape", _box(0, 0, 10, 10), "Rect", paint, None),
        ("shape", _box(20, 30, 20, 20), "Rect", paint, None),
    ), request=_theme_request())
    assert "W_LEGEND_SWATCH_COLLISION" in result[0]
    assert "W_LEGEND_COLOR_NOT_SEPARABLE:normal:0.0" in result[0]
