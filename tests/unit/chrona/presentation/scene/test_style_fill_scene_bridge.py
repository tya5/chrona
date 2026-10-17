from __future__ import annotations

from chrona.presentation.model.style_fills import StyleFillIndex
from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface
from chrona.presentation.scene.v05_builder import (
    _complete_surface_paint,
    _record_style_fill_overrides,
)


def _tokens():
    return ThemeTokenView({
        "version": "chrona/resolved-theme/v0.2",
        "kind": "resolved-theme",
        "body": {
            "values": {
                "canvas": {"type": "color", "value": "#FFFFFF"},
                "actual": {"type": "color", "value": "#334455"},
                "planned": {"type": "color", "value": "#556677"},
            },
            "roles": {
                "background": {"fill": "canvas"},
                "actual": {"fill": "actual"},
                "planned": {"fill": "planned"},
                # Selected roles may obtain their required fill from Style.
                "selected": {},
            },
            "metrics": {},
        },
    })


def _mark(scene_id, semantic, *, selected=True):
    return ScenePrimitive(
        scene_id, "Rect", "same-object", "object", semantic, semantic,
        (0.0, 0.0, 10.0, 4.0),
        **({"semantic_id": semantic, "theme_role": "selected"} if selected else {}))


def test_exact_repeated_occurrence_fills_join_to_emitted_scene_ids_only():
    row_a = StyleOccurrenceKey("same-object", "primary", "planned", "row-a", "item-a")
    row_b = StyleOccurrenceKey("same-object", "primary", "planned", "row-b", "item-a")
    style_fills = StyleFillIndex(((row_a, "#AA0000"), (row_b, "#0000AA")))
    overrides = {}
    _record_style_fill_overrides(overrides, style_fills, row_a, ("planned:row-a:item-a",))
    _record_style_fill_overrides(overrides, style_fills, row_b,
                                 ("planned:row-b:item-a:part0", "planned:row-b:item-a:part1"))

    surface = SceneSurface(
        "surface", (), (), (), None,
        (_mark("planned:row-a:item-a", "planned"),
         _mark("planned:row-b:item-a:part0", "planned"),
         _mark("planned:row-b:item-a:part1", "planned")),
        canvas_bounds=(0.0, 0.0, 20.0, 10.0),
    )
    completed = _complete_surface_paint(
        surface, _tokens(), style_fill_overrides=overrides)

    fills = {primitive.scene_id: primitive.paint.fill for primitive in completed.primitives}
    assert fills == {
        "planned:row-a:item-a": "#AA0000",
        "planned:row-b:item-a:part0": "#0000AA",
        "planned:row-b:item-a:part1": "#0000AA",
    }
    assert all(not hasattr(primitive, "style_occurrence_key")
               for primitive in completed.primitives)


def test_style_fill_precedes_actual_variance_and_absent_style_keeps_legacy_fill():
    key = StyleOccurrenceKey("same-object", "primary", "actual", "row-a", "item-a")
    fills = StyleFillIndex(((key, "#AA0000"),))
    overrides = {}
    _record_style_fill_overrides(overrides, fills, key, ("actual:row-a:item-a",))
    styled = _complete_surface_paint(
        SceneSurface("surface", (), (), (), None,
                     (_mark("actual:row-a:item-a", "actual"),),
                     canvas_bounds=(0.0, 0.0, 20.0, 10.0)),
        _tokens(), style_fill_overrides=overrides,
        actual_variance_paints={"same-object": "#00AA00"},
    )
    unstyled = _complete_surface_paint(
        SceneSurface("surface", (), (), (), None,
                     (_mark("actual:plain", "actual", selected=False),),
                     canvas_bounds=(0.0, 0.0, 20.0, 10.0)),
        _tokens(), actual_variance_paints={"same-object": "#00AA00"},
    )

    assert styled.primitives[0].paint.fill == "#AA0000"
    assert unstyled.primitives[0].paint.fill == "#00AA00"


def test_explicit_encoding_fills_inherited_outline_without_replacing_stroke():
    tokens = ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {
            "outline": {"type": "pattern", "value": {"kind": "outline"}},
            "stroke": {"type": "color", "value": "#334455"},
            "width": {"type": "number", "value": 2},
            "canvas": {"type": "color", "value": "#FFFFFF"},
        },
        "roles": {"planned": {"pattern": "outline", "stroke": "stroke", "strokeWidth": "width"},
                  "background": {"fill": "canvas"}},
        "metrics": {},
    }})
    primitive = _mark("planned:row-a:item-a", "planned", selected=False)
    completed = _complete_surface_paint(
        SceneSurface("surface", (), (), (), None, (primitive,),
                     canvas_bounds=(0.0, 0.0, 20.0, 10.0)),
        tokens, style_fill_overrides={primitive.scene_id: "#AA0000"},
    )
    assert completed.primitives[0].paint.fill == "#AA0000"
    assert completed.primitives[0].paint.stroke == "#334455"
    assert completed.primitives[0].paint.stroke_width == 2
