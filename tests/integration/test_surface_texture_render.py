"""Authored canvas textures and overlays survive real closure, SVG and PNG (#888)."""
from __future__ import annotations

import io
from copy import deepcopy
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

import pytest
import resvg_py
import yaml
from PIL import Image

from chrona.presentation.icons.importer import import_theme_assets
from chrona.presentation.model.closure import resolve_draft_render
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/surface-decoration"
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
SCANLINE_SOURCE = FIXTURES / "scanlines-theme-assets.yaml"
RICH_SVG = "chrona-output/visual/v0.6-svg"
RICH_PNG = "chrona-output/visual/v0.6-png"
FONT_FILES = tuple(str(ROOT / "src/chrona/resources/fonts" / filename) for filename in (
    "noto-sans-regular-v1.ttf", "noto-sans-bold-v1.ttf", "noto-sans-mono-regular-v1.ttf",
))


def _source(title: str) -> dict:
    project = sr.project({
        "task": sr.span("task", date(2026, 1, 5), 30, title="Texture test task"),
    })
    project["project"]["title"] = title
    return project


def _patch(name: str) -> dict:
    return yaml.safe_load((FIXTURES / f"{name}-surface-textures.yaml").read_text(encoding="utf-8"))


def _parts(name: str, *, roles: bool = True, seed_delta: int = 0,
           omit_roles: tuple[str, ...] = (), include_unused_tokens: bool = True) -> dict[str, dict]:
    parts = sr.bundle("executive-light")
    patch = _patch(name)
    theme = parts["theme"]
    body = theme["body"]
    if roles or include_unused_tokens:
        theme["version"] = patch["themePatch"]["version"]
        body["values"].update(deepcopy(patch["themePatch"]["values"]))
        parts["scheme"]["body"]["categories"].update(deepcopy(patch["schemePatch"]["categories"]))
    if seed_delta:
        seed_token = f"{name}.grain" if name == "montmartre" else f"{name}.rain"
        body["values"][seed_token]["value"]["seed"] += seed_delta
    if roles:
        role_values = deepcopy(patch["themePatch"]["roles"])
        for role in omit_roles:
            role_values.pop(role, None)
        body["roles"].update(role_values)
        bindings = deepcopy(patch["themePatch"]["colorBindings"])
        for role in omit_roles:
            bindings = {key: value for key, value in bindings.items()
                        if not key.startswith(f"{role}.")}
        body["colorBindings"].update(bindings)
    return parts


def _render(directory: Path, name: str, target: str, *, roles: bool = True,
            seed_delta: int = 0, omit_roles: tuple[str, ...] = (),
            include_unused_tokens: bool = True):
    directory.mkdir(parents=True, exist_ok=True)
    parts = _parts(name, roles=roles, seed_delta=seed_delta, omit_roles=omit_roles,
                   include_unused_tokens=include_unused_tokens)
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    project_path = sr._write(directory / "project.yaml", _source(name.title()))
    catalogues = [CATALOGUE]
    if name == "offworld" and (roles or include_unused_tokens):
        imported = directory / "scanline-catalog.json"
        provenance = import_theme_assets(SCANLINE_SOURCE, imported)
        assert provenance["set"] == "chrona-test-surface-textures" and provenance["patterns"] == 1
        catalogues.append(imported)
    profile = RICH_SVG if target == "svg" else RICH_PNG
    draft = resolve_draft_render(
        project_path=project_path, view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"],
        icon_catalog_paths=tuple(catalogues), viewport=(900, 560),
        target_kind=target, visual_profile=profile,
    )
    rendered = render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=None, draft_auto_block=draft.auto_block,
    ))
    suffix = "svg" if target == "svg" else "png"
    artifact_path = directory / f"{name}.{suffix}"
    artifact_path.write_bytes(rendered.artifact.content)
    if target == "svg":
        preview = resvg_py.svg_to_bytes(svg_string=rendered.artifact.content.decode("utf-8"), dpi=96,
                                        font_files=list(FONT_FILES), skip_system_fonts=True)
        (directory / f"{name}-preview.png").write_bytes(preview)
    print(f"{name} {target}: {artifact_path}")
    return rendered


def _role(review, role: str):
    return next(item for item in review.surface.primitives if item.visual_role == role)


def _assert_overlay_order(review, expected_roles: tuple[str, ...]) -> None:
    layers = {role: _role(review, role) for role in expected_roles}
    ordered = sorted(layers.values(), key=lambda item: item.paint_order)
    assert tuple(item.visual_role for item in ordered) == expected_roles
    content_orders = [item.paint_order for item in review.surface.primitives
                      if item.visual_role not in expected_roles and item.visual_role != "canvas-texture"]
    assert content_orders and min(item.paint_order for item in ordered) > max(content_orders)


@pytest.mark.parametrize(("name", "overlay_roles"), [
    ("montmartre", ("canvas-overlay-gradient", "canvas-overlay")),
    ("offworld", ("canvas-overlay",)),
])
@pytest.mark.parametrize(("target", "profile"), [("svg", RICH_SVG), ("png", RICH_PNG)])
def test_authored_surface_textures_are_deterministic_for_svg_and_native_png(
    tmp_path, name, overlay_roles, target, profile,
):
    if name == "offworld":
        patch = _patch(name)
        assert patch["themePatch"]["colorBindings"]["heading.fill"] == "category:offworld-text-light"
        assert patch["themePatch"]["colorBindings"]["tableColumnLabel.fill"] == "category:offworld-text-light"
        assert patch["schemePatch"]["categories"]["offworld-text-light"] == "#FFFFFF"
        assert "text.fill" not in patch["themePatch"]["colorBindings"]
    first = _render(tmp_path / "first", name, target)
    repeat = _render(tmp_path / "repeat", name, target)
    changed_seed = _render(tmp_path / "changed-seed", name, target, seed_delta=1)
    unstyled = _render(tmp_path / "unstyled", name, target, roles=False,
                       include_unused_tokens=False)

    assert first.artifact.target_kind == target and first.artifact.media_type == (
        "image/svg+xml" if target == "svg" else "image/png")
    assert first.artifact.content == repeat.artifact.content
    assert first.artifact.content != changed_seed.artifact.content
    assert first.surface.canvas_bounds == unstyled.surface.canvas_bounds, (
        "canvas overlay roles must not enlarge the completed canvas"
    )
    _assert_overlay_order(first, overlay_roles)
    assert all(_role(first, role).bounds == first.surface.canvas_bounds for role in overlay_roles)

    if name == "offworld":
        underlay = _role(first, "canvas-texture")
        assert underlay.paint.fill is None and underlay.paint.stroke is not None
        assert underlay.pattern is not None
        assert first.surface.canvas_paint.gradient is not None
    if name == "montmartre":
        assert first.surface.canvas_paint.fill is not None

    if target == "svg":
        root = ElementTree.fromstring(first.artifact.content)
        ns = {"s": "http://www.w3.org/2000/svg"}
        radial = root.find(".//s:radialGradient", ns)
        assert (radial is not None) == (name == "montmartre")
        for role in overlay_roles:
            node = next(item for item in root.iter() if item.get("data-purpose") == role)
            assert node.get("pointer-events") == "none"
            assert node.get("clip-path", "").startswith("url(#canvas-overlay-clip-")
        overlay_nodes = [next(item for item in root.iter() if item.get("data-purpose") == role)
                         for role in overlay_roles]
        svg_order = [item.get("data-purpose") for item in root.iter()
                     if item.get("data-purpose") in set(overlay_roles)]
        assert svg_order == list(overlay_roles)
        assert all(node.get("fill", "").startswith("url(#") for node in overlay_nodes)
    else:
        image = Image.open(io.BytesIO(first.artifact.content)).convert("RGB")
        left, top, width, height = first.surface.canvas_bounds
        assert (left, top) == (0, 0)
        assert image.size == (round(width), round(height))
        assert len(set(image.getdata())) > 3


@pytest.mark.parametrize(("name", "target"), [("montmartre", "svg"), ("offworld", "svg"),
                                                ("montmartre", "png"), ("offworld", "png")])
def test_omitting_authored_roles_preserves_the_unmodified_bundle_bytes(tmp_path, name, target):
    base = _render(tmp_path / "base", name, target, roles=False, include_unused_tokens=False)
    unused_tokens = _render(tmp_path / "unused-tokens", name, target, roles=False,
                            include_unused_tokens=True)

    assert base.artifact.content == unused_tokens.artifact.content
    assert not {item.visual_role for item in unused_tokens.surface.primitives} & {
        "canvas-overlay", "canvas-overlay-gradient", "canvas-texture",
    }


def test_offworld_horizon_gradient_shows_through_rain_holes_in_actual_png(tmp_path):
    complete = _render(tmp_path / "rain", "offworld", "png")
    without_rain = _render(tmp_path / "no-rain", "offworld", "png", omit_roles=("canvas-texture",))
    textured = Image.open(io.BytesIO(complete.artifact.content)).convert("RGB")
    bare = Image.open(io.BytesIO(without_rain.artifact.content)).convert("RGB")
    assert textured.size == bare.size

    content = [item.bounds for item in complete.surface.primitives
               if item.visual_role not in {"canvas-texture", "canvas-overlay"}]

    def outside_content(x: float, y: float) -> bool:
        return not any(w > 0 and h > 0 and left <= x <= left + w and top <= y <= top + h
                       for left, top, w, h in content)

    holes: dict[int, list[tuple[int, tuple[int, int, int]]]] = {}
    for y in range(1, textured.height - 1):
        for x in range(1, textured.width - 1):
            if (outside_content(x + 0.5, y + 0.5)
                    and textured.getpixel((x, y)) == bare.getpixel((x, y))):
                holes.setdefault(x, []).append((y, textured.getpixel((x, y))))
    visible_gradient = any(
        samples[-1][1] != samples[0][1]
        for samples in holes.values() if len(samples) > 1
    )
    assert visible_gradient, "no clear rain-hole pixels showed the underlying horizon gradient"
