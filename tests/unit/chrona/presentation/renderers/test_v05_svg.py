from datetime import date

from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface, SurfaceScaleManifest


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
