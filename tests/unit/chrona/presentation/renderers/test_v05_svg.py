from datetime import date

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface, SurfaceScaleManifest, TextLayout


def test_svg_formats_completed_surface_with_declared_role_only():
    theme = {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {"metrics": {},
        "values": {"surface": {"type": "color", "value": "#ffffff"}, "ink": {"type": "color", "value": "#000000"}},
        "roles": {"background": {"fill": "surface"}, "planned": {"fill": "ink"}}}}
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    surface = SceneSurface("s", (), (), (), scale, (ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4)),))
    assert 'data-scene-id="p"' in render_v05_svg(surface, viewport=(10, 10), tokens=ThemeTokenView(theme))


def test_svg_emits_only_the_declared_dependency_marker_used_by_a_completed_path():
    theme = {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {"metrics": {},
        "values": {"surface": {"type": "color", "value": "#ffffff"}, "ink": {"type": "color", "value": "#000000"}},
        "roles": {"background": {"fill": "surface"}, "dependency": {"stroke": "ink"}}}}
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    surface = SceneSurface("s", (), (), (), scale, (ScenePrimitive("relation:r", "Path", "r", "relation", "dependency", "dependency", (0, 0, 0, 0), shape="triangle", points=((1, 1), (9, 9))),))
    output = render_v05_svg(surface, viewport=(10, 10), tokens=ThemeTokenView(theme))
    assert '<marker id="marker-dependency-triangle"' in output
    assert 'marker-end="url(#marker-dependency-triangle)"' in output


def test_svg_serializes_declared_outline_and_hatch_forms_without_role_inference():
    theme = {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {"metrics": {},
        "values": {"surface": {"type": "color", "value": "#ffffff"}, "ink": {"type": "color", "value": "#000000"},
                   "outline": {"type": "pattern", "value": "outline"}, "hatch": {"type": "pattern", "value": "diagonal-hatch"}},
        "roles": {"background": {"fill": "surface"}, "planned": {"fill": "ink", "stroke": "ink", "pattern": "outline"},
                  "missingActual": {"fill": "ink", "stroke": "ink", "pattern": "hatch"}}}}
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    surface = SceneSurface("s", (), (), (), scale, (
        ScenePrimitive("planned", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4)),
        ScenePrimitive("missing", "Rect", "b", "object", "missingActual", "missingActual", (5, 2, 3, 4)),
    ))
    output = render_v05_svg(surface, viewport=(10, 10), tokens=ThemeTokenView(theme))
    assert 'data-scene-id="planned"' in output and 'fill="none" stroke="#000000"' in output
    assert '<pattern id="pattern-missingActual-diagonal-hatch"' in output
    assert 'data-scene-id="missing"' in output and 'fill="url(#pattern-missingActual-diagonal-hatch)"' in output


def test_svg_projects_completed_multiline_text_without_rewrapping():
    theme = {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {"metrics": {},
        "values": {"surface": {"type": "color", "value": "#ffffff"}, "ink": {"type": "color", "value": "#000000"}},
        "roles": {"background": {"fill": "surface"}, "label": {"fill": "ink"}}}}
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    layout = TextLayout((1, 2, 9, 20), (1, 10), ("one", "two"), "Noto Sans", 400, 10, 1.2, "font")
    primitive = ScenePrimitive("label:a", "Text", "a", "object", "label", "label", layout.bounds,
                               text="one two", baseline=layout.baseline, text_layout=layout)
    output = render_v05_svg(SceneSurface("s", (), (), (), scale, (primitive,)), viewport=(10, 30), tokens=ThemeTokenView(theme))
    assert '<tspan x="1" dy="0">one</tspan><tspan x="1" dy="12">two</tspan>' in output
