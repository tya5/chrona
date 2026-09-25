from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import SceneIconPath, ScenePaint, ScenePrimitive, SceneSurface


def _surface(icon: ScenePrimitive) -> SceneSurface:
    return SceneSurface("test", (), (), (), None, (icon,), ScenePaint("#ffffff", None, None, (), 1.0),
                        canvas_bounds=(0, 0, 24, 24))


def test_svg_serializes_completed_vector_icon_without_source_svg():
    icon = ScenePrimitive("i", "Icon", "risk", "object", "icon-mark", "planned", (1, 2, 12, 12),
                          paint=ScenePaint("#123456", None, None, (), 1.0), icon_kind="vector",
                          icon_asset_identity="sha256:" + "a" * 64, icon_paths=(SceneIconPath(
                              (("move", ((1, 2),)), ("line", ((13, 14),)), ("close", ())), "#123456", None, None),),
                          icon_alternative="Risk", icon_decorative=False, icon_viewport=(24, 24))
    svg = render_v05_svg(_surface(icon))
    assert 'data-asset-identity="sha256:' in svg and 'aria-label="Risk"' in svg and "M1 2L13 14Z" in svg


def test_svg_serializes_completed_stroke_icon_path_with_layout_scale():
    icon = ScenePrimitive("i", "Icon", "risk", "object", "icon-mark", "planned", (1, 2, 12, 12),
                          paint=ScenePaint("#123456", None, None, (), 1.0), icon_kind="vector",
                          icon_asset_identity="sha256:" + "a" * 64, icon_paths=(SceneIconPath(
                              (("move", ((1, 2),)), ("line", ((13, 14),))), None, "#123456", 1.0, "round", "bevel"),),
                          icon_alternative="Risk", icon_decorative=False, icon_viewport=(24, 24))
    svg = render_v05_svg(_surface(icon))
    assert 'fill="none"' in svg and 'stroke="#123456"' in svg and 'stroke-width="1"' in svg
    assert 'stroke-linecap="round"' in svg and 'stroke-linejoin="bevel"' in svg
