"""Target-kind renderer selection and optional CairoSVG conversion."""
from __future__ import annotations

from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from typing import Any

from chrona.core.ports import RenderArtifact, Renderer
from chrona.presentation.model.font_metrics import FontFile, FontMetricsError, resolve_font_files
from chrona.presentation.model.font_resources import FontAssetResolver
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.renderers.v05_typeset import V05TikzRenderer, V05TypstRenderer


def _failure(code: str, detail: str) -> ValueError:
    """Keep stable diagnostic codes while naming the renderer contract that failed."""
    return ValueError(f"{code}: {detail}")


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


class ResvgPngRenderer:
    """PNG serialization with the bundled resvg engine only."""

    def __init__(self, target_kind: str, descriptor: dict[str, Any], font_metrics: dict[str, Any] | None,
                 asset_root: Path | None, font_files: tuple[FontFile, ...] | None = None,
                 asset_resolver: FontAssetResolver | None = None):
        self.target_kind = target_kind
        self._descriptor = descriptor
        self._font_metrics = font_metrics
        self._asset_root = asset_root
        self._font_files_override = font_files
        self._asset_resolver = asset_resolver

    def render(self, surface: object) -> RenderArtifact:
        _verify_resvg(self._descriptor)
        files, identities = _font_files(self._font_metrics, self._asset_root, self._font_files_override,
                                        self._asset_resolver)
        svg = V05SvgRenderer(viewer_fit=False).render(surface).content
        try:
            import resvg_py
            content = resvg_py.svg_to_bytes(svg_string=svg.decode("utf-8"), dpi=self._descriptor["dpi"],
                                            font_files=list(dict.fromkeys(str(item.path) for item in files)),
                                            skip_system_fonts=True)
        except ImportError as error:
            raise _failure("E_RENDER_RASTERIZER_UNAVAILABLE", "target PNG requires the installed resvg_py adapter") from error
        return RenderArtifact("png", "image/png", content, _adapter_identity(
            f"resvg-py-{self._descriptor['version']}-resvg-{self._descriptor['resvgVersion']}", identities))


class ReportLabPdfRenderer:
    """Deterministic PDF serialization of the completed SVG surface."""

    target_kind = "pdf"

    def __init__(self, descriptor: dict[str, Any], font_metrics: dict[str, Any] | None, asset_root: Path | None,
                 asset_resolver: FontAssetResolver | None = None):
        self._descriptor = descriptor
        self._font_metrics = font_metrics
        self._asset_root = asset_root
        self._asset_resolver = asset_resolver

    def render(self, surface: object) -> RenderArtifact:
        _verify_reportlab(self._descriptor)
        files, identities = _font_files(self._font_metrics, self._asset_root,
                                        asset_resolver=self._asset_resolver)
        svg = V05SvgRenderer(viewer_fit=False).render(surface).content
        try:
            from reportlab import rl_config
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.graphics import renderPDF
            from svglib.svglib import svg2rlg
            for item in files:
                pdfmetrics.registerFont(TTFont(_reportlab_font_name(item.family, item.weight), str(item.path)))
            for family in {item.family for item in files}:
                faces = {item.weight: _reportlab_font_name(item.family, item.weight)
                         for item in files if item.family == family}
                if 400 in faces:
                    pdfmetrics.registerFontFamily(family, normal=faces[400],
                                                  bold=faces.get(700, faces[400]))
            rl_config.invariant = 1
            content = renderPDF.drawToString(svg2rlg(BytesIO(svg)))
        except ImportError as error:
            raise _failure("E_RENDER_RASTERIZER_UNAVAILABLE", "target PDF requires installed svglib and reportlab adapters") from error
        return RenderArtifact("pdf", "application/pdf", content, _adapter_identity(
            f"svglib-{self._descriptor['svglibVersion']}-reportlab-{self._descriptor['reportlabVersion']}-invariant", identities))


def renderer_for(target: dict[str, Any], environment: dict[str, Any], *, asset_root: Path | None = None,
                 font_files: tuple[FontFile, ...] | None = None,
                 asset_resolver: FontAssetResolver | None = None) -> Renderer:
    kind = target["kind"]
    supported = {
        "svg": {"accessibleText", "hierarchicalAxis", "marker", "semanticRoles", "sourceMetadata", "tableSemantics"},
        "png": set(),
        "pdf": {"accessibleText"},
        "typst": set(),
        "tikz": set(),
    }
    if not set(target.get("capabilities", ())).issubset(supported.get(kind, set())):
        missing = sorted(set(target.get("capabilities", ())) - supported.get(kind, set()))
        raise _failure("E_OUTPUT_CAPABILITY_MISSING", f"target kind {_brief(kind)} does not support requested capabilities {missing[:8]!r}{'…' if len(missing) > 8 else ''}")
    if kind == "svg":
        return V05SvgRenderer()
    if kind == "png":
        descriptor = environment.get("rasterizer")
        if not isinstance(descriptor, dict):
            raise _failure("E_RENDER_RASTERIZER_IDENTITY", "target PNG requires an environment rasterizer descriptor mapping")
        return ResvgPngRenderer(kind, descriptor, environment.get("fontMetrics"), asset_root, font_files,
                                asset_resolver)
    if kind == "pdf":
        descriptor = environment.get("rasterizer")
        if not isinstance(descriptor, dict):
            raise _failure("E_RENDER_RASTERIZER_IDENTITY", "target PDF requires an environment rasterizer descriptor mapping")
        return ReportLabPdfRenderer(descriptor, environment.get("fontMetrics"), asset_root, asset_resolver)
    if kind in {"typst", "tikz"}:
        descriptor = environment.get("typesetter")
        expected = ("typst", "chrona-typst/v0.1") if kind == "typst" else ("tectonic", "chrona-tikz/v0.1")
        if not isinstance(descriptor, dict) or (descriptor.get("engine"), descriptor.get("adapterGrammar")) != expected:
            actual = (descriptor.get("engine"), descriptor.get("adapterGrammar")) if isinstance(descriptor, dict) else type(descriptor).__name__
            raise _failure("E_RENDER_TYPESETTER_IDENTITY", f"target {kind!r} requires engine={expected[0]!r}, adapterGrammar={expected[1]!r}; received {actual!r}")
        return V05TypstRenderer() if kind == "typst" else V05TikzRenderer()
    raise _failure("E_PRESENTATION_TARGET", f"unsupported target kind {_brief(kind)}; supported kinds are {sorted(supported)!r}")


def _font_files(descriptor: dict[str, Any] | None, asset_root: Path | None,
                override: tuple[FontFile, ...] | None = None,
                asset_resolver: FontAssetResolver | None = None):
    if override is not None:
        return override, tuple(sorted(item.content_identity for item in override))
    if not isinstance(descriptor, dict):
        raise _failure("E_RENDER_FONT_CLOSURE", "fontMetrics must be a descriptor mapping unless explicit closed font files are supplied")
    return resolve_font_files(descriptor, asset_root=asset_root, asset_resolver=asset_resolver)


def _reportlab_font_name(family: str, weight: int) -> str:
    return family if weight == 400 else f"{family}-{weight}"
def _adapter_identity(prefix: str, identities: tuple[str, ...]) -> str:
    return prefix + "-fonts-" + ".".join(identity.removeprefix("sha256:") for identity in identities)


def _verify_resvg(descriptor: dict[str, Any]) -> None:
    try:
        import resvg_py
    except ImportError as error:
        raise _failure("E_RENDER_RASTERIZER_UNAVAILABLE", "resvg_py could not be imported for rasterizer verification") from error
    if (descriptor.get("engine") != "resvg-py" or descriptor.get("version") != resvg_py.__version__
            or descriptor.get("resvgVersion") != resvg_py.__resvg_version__):
        raise _failure("E_RENDER_RASTERIZER_IDENTITY", f"descriptor engine/version/resvgVersion must match installed resvg_py ({resvg_py.__version__!r}, {resvg_py.__resvg_version__!r})")


def _verify_reportlab(descriptor: dict[str, Any]) -> None:
    try:
        actual = (version("svglib"), version("reportlab"))
    except Exception as error:
        raise _failure("E_RENDER_RASTERIZER_UNAVAILABLE", "installed svglib/reportlab versions could not be inspected") from error
    if (descriptor.get("engine") != "reportlab" or descriptor.get("invariant") is not True
            or actual != (descriptor.get("svglibVersion"), descriptor.get("reportlabVersion"))):
        raise _failure("E_RENDER_RASTERIZER_IDENTITY", f"descriptor must select invariant reportlab and installed (svglib, reportlab) versions {actual!r}")
