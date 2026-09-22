"""Target-kind renderer selection and optional CairoSVG conversion."""
from __future__ import annotations

from importlib.metadata import version
from io import BytesIO
from typing import Any

from chrona.core.ports import RenderArtifact, Renderer
from chrona.presentation.renderers.v05_svg import V05SvgRenderer


class CairoSvgRenderer:
    """Raster/PDF adapter that converts the completed SVG serialization only."""

    def __init__(self, target_kind: str, descriptor: dict[str, Any]):
        self.target_kind = target_kind
        self._descriptor = descriptor

    def render(self, surface: object, *, viewport: tuple[float, float], tokens: object) -> RenderArtifact:
        _verify_cairo(self._descriptor)
        svg = V05SvgRenderer().render(surface, viewport=viewport, tokens=tokens).content
        try:
            import cairosvg
            convert = {"png": cairosvg.svg2png, "pdf": cairosvg.svg2pdf}[self.target_kind]
            content = convert(bytestring=svg, dpi=self._descriptor["dpi"])
        except ImportError as error:
            raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE") from error
        except KeyError as error:
            raise ValueError("E_PRESENTATION_TARGET") from error
        media_type = "image/png" if self.target_kind == "png" else "application/pdf"
        return RenderArtifact(self.target_kind, media_type, content, f"cairosvg-{self._descriptor['version']}-cairo-{self._descriptor['cairoVersion']}")


class ReportLabPdfRenderer:
    """Deterministic PDF serialization of the completed SVG surface."""

    target_kind = "pdf"

    def __init__(self, descriptor: dict[str, Any]):
        self._descriptor = descriptor

    def render(self, surface: object, *, viewport: tuple[float, float], tokens: object) -> RenderArtifact:
        _verify_reportlab(self._descriptor)
        svg = V05SvgRenderer().render(surface, viewport=viewport, tokens=tokens).content
        try:
            from reportlab import rl_config
            from reportlab.graphics import renderPDF
            from svglib.svglib import svg2rlg
            rl_config.invariant = 1
            content = renderPDF.drawToString(svg2rlg(BytesIO(svg)))
        except ImportError as error:
            raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE") from error
        return RenderArtifact("pdf", "application/pdf", content, f"svglib-{self._descriptor['svglibVersion']}-reportlab-{self._descriptor['reportlabVersion']}-invariant")


def renderer_for(target: dict[str, Any], environment: dict[str, Any]) -> Renderer:
    kind = target["kind"]
    supported = {
        "svg": {"accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata", "tableSemantics"},
        "png": set(),
        "pdf": {"accessibleText"},
    }
    if not set(target.get("capabilities", ())).issubset(supported.get(kind, set())):
        raise ValueError("E_OUTPUT_CAPABILITY_MISSING")
    if kind == "svg":
        return V05SvgRenderer()
    if kind == "png":
        descriptor = environment.get("rasterizer")
        if not isinstance(descriptor, dict):
            raise ValueError("E_RENDER_RASTERIZER_IDENTITY")
        return CairoSvgRenderer(kind, descriptor)
    if kind == "pdf":
        descriptor = environment.get("rasterizer")
        if not isinstance(descriptor, dict):
            raise ValueError("E_RENDER_RASTERIZER_IDENTITY")
        return ReportLabPdfRenderer(descriptor)
    raise ValueError("E_PRESENTATION_TARGET")


def _verify_cairo(descriptor: dict[str, Any]) -> None:
    try:
        import cairocffi
        import cairosvg
    except ImportError as error:
        raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE") from error
    if (descriptor.get("engine") != "cairosvg" or descriptor.get("version") != cairosvg.__version__
            or descriptor.get("cairoVersion") != cairocffi.cairo_version_string()):
        raise ValueError("E_RENDER_RASTERIZER_IDENTITY")


def _verify_reportlab(descriptor: dict[str, Any]) -> None:
    try:
        actual = (version("svglib"), version("reportlab"))
    except Exception as error:
        raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE") from error
    if (descriptor.get("engine") != "reportlab" or descriptor.get("invariant") is not True
            or actual != (descriptor.get("svglibVersion"), descriptor.get("reportlabVersion"))):
        raise ValueError("E_RENDER_RASTERIZER_IDENTITY")
