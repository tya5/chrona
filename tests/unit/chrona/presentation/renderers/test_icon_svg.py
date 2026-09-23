from chrona.presentation.icons import normalize_icon
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface


def _surface(icon: ScenePrimitive) -> SceneSurface:
    return SceneSurface("test", (), (), (), None, (icon,), ScenePaint("#ffffff", None, None, (), 1.0))


def test_svg_serializes_completed_vector_icon_without_source_svg():
    vector = normalize_icon("vector", b'<svg viewBox="0 0 24 24"><path d="M0 0L24 24Z"/></svg>', (24, 24))
    icon = ScenePrimitive("i", "Icon", "risk", "object", "icon-mark", "planned", (1, 2, 12, 12),
                          paint=ScenePaint("#123456", None, None, (), 1.0), icon_kind="vector",
                          icon_asset_identity="sha256:" + "a" * 64, icon_vector=vector,
                          icon_alternative="Risk", icon_decorative=False)
    svg = render_v05_svg(_surface(icon), viewport=(24, 24))
    assert 'data-asset-identity="sha256:' in svg and 'aria-label="Risk"' in svg and "M1 2L13 14Z" in svg
