import pytest
from datetime import date
from types import SimpleNamespace

from chrona.presentation.layout.mark_geometry import MarkFacetAbsence, compose_item_marks, glyph_parts, symbol_parts
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.surface_quality import PathCommand, ScalePlacement
from chrona.presentation.model.projection import ObservationState


def test_scene_projects_intrinsic_finish_metadata_without_reclassifying_role_outline_width():
    from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
    from chrona.presentation.scene.v05_builder import _symbol_primitives

    commands = (PathCommand("move", ((0.0, 0.0),)),
                PathCommand("line", ((10.0, 0.0),)),
                PathCommand("line", ((5.0, 10.0),)),
                PathCommand("line", ((0.0, 0.0),)))
    intrinsic = SymbolPartPlacement(commands, "stroke", stroke_width=0.75,
                                    line_cap="round", line_join="bevel")
    role_outline = SymbolPartPlacement(commands, "stroke", stroke_width=2.0)
    originals = (intrinsic, role_outline)
    projected = _symbol_primitives("gate", "point", "object", "mark", "gate",
                                   (0, 0, 10, 10), originals)

    assert projected[0].glyph_stroke_width == 0.75
    assert projected[0].glyph_line_cap == "round"
    assert projected[0].glyph_line_join == "bevel"
    assert projected[1].glyph_stroke_width is None
    assert projected[1].glyph_line_cap is None and projected[1].glyph_line_join is None
    assert projected[1].glyph_paint_mode == "stroke" and projected[1].visual_role == "gate"
    assert projected[1].symbol.outline == commands
    assert role_outline.stroke_width == 2.0


def _glyph(*parts):
    return {"shape": "glyph", "viewBox": [10, 10], "parts": list(parts)}


def test_glyph_parts_fits_the_view_box_contain_and_centred_into_wider_bounds():
    parts = glyph_parts(_glyph({"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"}), (0, 0, 40, 20))
    assert len(parts) == 1
    points = [command.points[0] for command in parts[0].outline]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    # 10x10 viewBox scaled to fit 40x20 bounds: scale=2, centred inline (offset 10).
    assert min(xs) == pytest.approx(10.0)
    assert max(xs) == pytest.approx(30.0)
    assert min(ys) == pytest.approx(0.0)
    assert max(ys) == pytest.approx(20.0)


def test_glyph_parts_omits_a_part_declaring_no_paint():
    parts = glyph_parts(_glyph({"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"},
                               {"d": "M2 2L8 2L8 8L2 8Z", "paint": "none"}),
                        (0, 0, 10, 10))
    assert len(parts) == 1


def test_glyph_parts_carries_each_part_paint_mode_and_optional_literal_color():
    parts = glyph_parts(_glyph({"d": "M0 0L10 0L10 10L0 10Z", "paint": "fill"},
                               {"d": "M2 2L8 2L8 8L2 8Z", "paint": "stroke", "color": "#1B1B1B"}),
                        (0, 0, 10, 10))
    assert [part.paint for part in parts] == ["fill", "stroke"]
    assert parts[0].color is None
    assert parts[1].color == "#1B1B1B"


def test_glyph_parts_rejects_a_curved_part_not_yet_supported():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts(_glyph({"d": "M0 0C1 1 2 2 3 3", "paint": "fill"}), (0, 0, 10, 10))


def test_glyph_parts_rejects_a_missing_view_box():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts({"shape": "glyph", "parts": [{"d": "M0 0L1 1Z", "paint": "fill"}]}, (0, 0, 10, 10))


def test_glyph_parts_rejects_empty_parts():
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        glyph_parts({"shape": "glyph", "viewBox": [10, 10], "parts": []}, (0, 0, 10, 10))


def test_symbol_geometry_is_completed_in_layout_from_the_full_value_mapping():
    geometry = symbol_parts({"shape": "diamond"}, (0, 0, 10, 10))
    assert geometry[0].commands


def test_layout_symbol_geometry_keeps_glyph_parts_as_typed_paint_intents():
    parts = symbol_parts(_glyph({"d": "M0 0L1 1Z", "paint": "fill"}), (0, 0, 10, 10))
    assert parts[0].paint_mode == "fill"


def test_built_in_mark_uses_layout_completed_outline_while_glyph_owns_its_outline():
    completed = (PathCommand("move", ((1.0, 2.0),)), PathCommand("line", ((3.0, 4.0),)))
    assert symbol_parts({"shape": "diamond"}, (0, 0, 10, 10), completed)[0].commands == completed
    glyph = symbol_parts(_glyph({"d": "M0 0L10 0L10 10Z", "paint": "fill"}),
                         (0, 0, 10, 10), completed)[0]
    assert glyph.commands != completed


def test_item_composer_closes_planned_open_actual_missing_actual_and_absences():
    scale = ScalePlacement("surface", "primary", date(2026, 1, 1), date(2026, 2, 1),
                           100.0, 162.0, 100.0, 2.0)
    roles = {
        "planned": MarkGeometry(0.5, 0.25, 0, 0.0),
        "snapshot": MarkGeometry(0.5, 0.25, 0, 0.0),
        "actual": MarkGeometry(0.4, 0.6, 1, 0.0),
        "missing-actual": MarkGeometry(0.4, 0.6, 2, 0.0),
    }
    frame = MarkBandFrame.zero_origin(scale, 10.0, roles)
    theme = SimpleNamespace(variant_symbol=lambda _role: {"shape": "circle"})
    item = SimpleNamespace(
        object_id="task", source_type="span",
        planned={"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        actual={"start": date(2026, 1, 2), "openUntil": "asOf"},
        observation_state=ObservationState.RECORDED,
    )

    completed = compose_item_marks(item=item, instance_id="row:task", source_kind="combined",
                                   frame=frame, as_of=date(2026, 1, 5), theme_tokens=theme,
                                   slot_id="timeline")
    planned, actual = completed.marks
    assert (planned.bounds.inline, planned.bounds.inline_size) == (100, 8)
    assert planned.start_port == (100.0, 5.0)
    assert (actual.bounds.inline, actual.bounds.inline_size) == (102, 6)
    assert actual.end_port == (108.0, 8.0)
    assert actual.end_treatment == "open"
    assert len(actual.symbol_parts) == 1
    assert actual.symbol_parts[0].commands == actual.path_commands
    assert completed.diagnostics == ()
    assert completed.absences == ()

    missing_item = SimpleNamespace(
        object_id="gate", source_type="point", planned={"at": date(2026, 1, 3)},
        actual=None, observation_state=ObservationState.DUE_UNOBSERVED,
    )
    missing = compose_item_marks(item=missing_item, instance_id="row:gate", source_kind="combined",
                                 frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline")
    assert [mark.placement_id for mark in missing.marks] == ["planned:row:gate", "missing-actual:row:gate"]
    assert missing.marks[1].bounds.inline == 104

    as_of_required = compose_item_marks(item=item, instance_id="row:task", source_kind="combined",
                                        frame=frame, as_of=None, theme_tokens=theme, slot_id="timeline")
    assert as_of_required.diagnostics == ("W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:task",)
    assert as_of_required.absences == (MarkFacetAbsence("actual", "as-of-required"),)


def test_actual_open_span_uses_completed_duration_outline_not_milestone_variant():
    scale = ScalePlacement("surface", "primary", date(2026, 1, 1), date(2026, 2, 1),
                           100.0, 162.0, 100.0, 2.0)
    roles = {name: MarkGeometry(0.5, 0.25, 0, 0.0)
             for name in ("planned", "snapshot", "actual", "missing-actual")}
    frame = MarkBandFrame.zero_origin(scale, 10.0, roles)

    class PointOnlyTheme:
        def variant_symbol(self, _role):
            raise AssertionError("milestone symbols are point geometry only")

    item = SimpleNamespace(
        object_id="task", source_type="span",
        planned={"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
        actual={"start": date(2026, 1, 2), "openUntil": "asOf"},
        observation_state=ObservationState.RECORDED,
    )
    result = compose_item_marks(item=item, instance_id="row:task", source_kind="combined",
                                frame=frame, as_of=date(2026, 1, 5), theme_tokens=PointOnlyTheme(),
                                slot_id="timeline")
    actual = next(mark for mark in result.marks if mark.semantic_id == "actual")
    assert actual.mark_shape == "open-span"
    assert actual.path_commands
    assert len(actual.symbol_parts) == 1
    assert actual.symbol_parts[0].commands == actual.path_commands
    assert actual.placement_id == "actual:row:task"


def test_actual_point_continues_to_use_the_theme_milestone_glyph():
    scale = ScalePlacement("surface", "primary", date(2026, 1, 1), date(2026, 2, 1),
                           100.0, 162.0, 100.0, 2.0)
    roles = {name: MarkGeometry(0.5, 0.25, 0, 0.0)
             for name in ("planned", "snapshot", "actual", "missing-actual")}
    frame = MarkBandFrame.zero_origin(scale, 10.0, roles)
    requests = []

    class GlyphTheme:
        def variant_symbol(self, role):
            requests.append(role)
            return _glyph({"d": "M0 0L10 0L10 10Z", "paint": "fill"},
                          {"d": "M2 2L8 2L8 8Z", "paint": "stroke"})

        def has_role(self, _role):
            return False

        def has_binding(self, _role, _member):
            return False

    item = SimpleNamespace(
        object_id="gate", source_type="point",
        planned={"at": date(2026, 1, 3)}, actual={"at": date(2026, 1, 4)},
        observation_state=ObservationState.RECORDED,
    )
    result = compose_item_marks(item=item, instance_id="row:gate", source_kind="combined",
                                frame=frame, as_of=date(2026, 1, 5), theme_tokens=GlyphTheme(),
                                slot_id="timeline")
    actual = next(mark for mark in result.marks if mark.semantic_id == "actual")
    assert requests == ["planned", "actual"]
    assert actual.mark_shape == "point"
    assert len(actual.symbol_parts) == 2
