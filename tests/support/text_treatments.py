"""Synthetic fixtures for the #585 text treatments (horizontal compression, vertical writing).

A Project goes through the packaged preset bundle with a Theme that declares a treatment on a few roles.
Nothing here reads `examples/`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.resources import safe_load
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
CJK_DESCRIPTOR = ROOT / "packages/chrona-fonts-noto-cjk/src/chrona_fonts_noto_cjk/font-metrics.yaml"
JP = "Noto Sans JP, sans-serif"


def cjk_available() -> bool:
    return CJK_DESCRIPTOR.is_file()


def with_scale(parts: dict[str, dict[str, Any]], roles: Iterable[str] | None = None, value: Any = 0.6, *,
               token: str = "h-scale") -> list[str]:
    """Bind `horizontalScale` to a number token on each named role (default: every role that has a font size)."""
    theme = parts["theme"]["body"]
    declared = [role for role, binding in theme["roles"].items() if "fontSize" in binding and (roles is None or role in roles)]
    theme["values"][token] = {"type": "number", "value": value}
    for role in declared:
        theme["roles"][role]["horizontalScale"] = token
    return declared


def with_vertical_groups(parts: dict[str, dict[str, Any]], *, header_text: str | None = None, family: str | None = None,
                         size: float | None = None, mode: str = "vertical") -> None:
    """Declare `writingMode` on the group-label role (and optionally its family, size and the View's label template)."""
    theme = parts["theme"]["body"]
    theme["values"]["tag-writing-mode"] = {"type": "writingMode", "value": mode}
    role = theme["roles"]["groupHeader"]
    role["writingMode"] = "tag-writing-mode"
    if family is not None:
        theme["values"]["tag-family"] = {"type": "fontFamily", "value": family}
        role["fontFamily"] = "tag-family"
    if size is not None:
        theme["values"]["tag-size"] = {"type": "number", "value": size}
        role["fontSize"] = "tag-size"
    if header_text is not None:
        parts["view"]["body"]["grouping"]["header"] = {"text": header_text}


def render(directory: Path, source: Mapping[str, Any], parts: Mapping[str, Mapping[str, Any]], *, cjk: bool = False,
           viewport: tuple[int, int | None] = (1600, 900)) -> Any:
    """`synthetic_review.render`, optionally with Noto Sans JP declared beside the bundled faces."""
    if not cjk:
        return sr.render(directory, source, presentation=parts, viewport=viewport)
    descriptor = safe_load((ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml").read_bytes())
    descriptor["assets"] = [*descriptor["assets"], *safe_load(CJK_DESCRIPTOR.read_bytes())["assets"]]
    descriptor_path = directory / "font-metrics.yaml"
    descriptor_path.write_text(yaml.safe_dump(descriptor, sort_keys=False), encoding="utf-8")
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=sr._write(directory / "project.yaml", source), view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], viewport=viewport, font_metrics_path=descriptor_path)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


def texts(rendered: Any) -> dict[str, Any]:
    """The Text primitives of a render by scene id."""
    return {item.scene_id: item for item in rendered.surface.primitives if item.kind.value == "Text"}


def widths(rendered: Any) -> Mapping[str, float]:
    return {scene_id: item.bounds[2] for scene_id, item in texts(rendered).items()}
