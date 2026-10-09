"""Heading and frame-glyph glow keeps its existing rich-paint ladder (#1237)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import io
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops
import pytest
import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
FIXTURE = ROOT / "tests/fixtures/surface-decoration/marquee-glyph-frame.yaml"
SVG = "chrona-output/visual/v0.6-svg"
PNG = "chrona-output/visual/v0.6-png"
BASELINE = "chrona-output/visual/v0.5-baseline"
GLOW_FILL = "#FFDA63"


def _catalogue(directory: Path) -> Path:
    """Use the same catalogue identity with a private fill-only glyph for baseline tests."""
    document = yaml.safe_load(CATALOGUE.read_text(encoding="utf-8"))
    document["body"]["glyphs"]["bulb"] = {
        "viewport": {"inlineSize": 16, "blockSize": 16},
        "parts": [{"data": "M 2 2 L 14 2 L 14 14 L 2 14 Z", "paint": "fill"}],
    }
    path = directory / "neutral-catalogue.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def _presentation(*, headings: bool = True, heading_glow: bool = False, frame_glow: bool = False,
                  glow: bool = True, fidelity: str = "required", opacity_only: bool = False,
                  fidelity_only: bool = False, omit_fill: str | None = None) -> dict:
    parts = sr.bundle("executive-light")
    fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    node = deepcopy(fixture["layoutNode"])
    parts["layout"]["root"]["children"][0] = node
    theme = parts["theme"]["body"]
    patch = fixture["themePatch"]
    parts["theme"]["version"] = patch["version"]
    theme["values"].update(deepcopy(patch["values"]))
    theme["roles"]["region-frame-marquee"] = deepcopy(patch["roles"]["region-frame-marquee"])
    theme["roles"]["frame-glyph-marquee"] = deepcopy(patch["roles"]["frame-glyph-marquee"])
    theme["colorBindings"].update(deepcopy(patch["colorBindings"]))
    parts["scheme"]["body"]["categories"].update(deepcopy(fixture["schemePatch"]["categories"]))
    if headings:
        parts["view"]["body"]["heading"] = {
            "kicker": "MARQUEE", "title": "Glow title", "subtitle": "Bulbs in a frame",
        }
        theme["roles"].setdefault("kicker", deepcopy(theme["roles"]["heading"]))
        theme["roles"].setdefault("subtitle", deepcopy(theme["roles"]["heading"]))
        for role_name in ("heading", "kicker", "subtitle"):
            theme["colorBindings"].setdefault(f"{role_name}.fill", "category:marquee-text")

    if glow:
        theme["values"].update({
            "test-glow-blur": {"type": "number", "value": 5},
            "test-glow-opacity": {"type": "number", "value": 0.85},
            "test-glow-fidelity": {"type": "fidelity", "value": fidelity},
            "test-role-opacity": {"type": "number", "value": 1.0},
        })
        targets = []
        if heading_glow:
            targets.extend(("heading", "kicker", "subtitle"))
        if frame_glow:
            targets.append("frame-glyph-marquee")
        for role_name in targets:
            role = theme["roles"].setdefault(role_name, {})
            if opacity_only:
                role["opacity"] = "test-role-opacity"
            if not opacity_only and not fidelity_only:
                role["glowBlur"] = "test-glow-blur"
                role["glowOpacity"] = "test-glow-opacity"
            if not opacity_only:
                role["glowFidelity"] = "test-glow-fidelity"
            if role_name in {"heading", "kicker", "subtitle"}:
                if omit_fill != role_name:
                    theme["colorBindings"][f"{role_name}.fill"] = "category:marquee-text"
                else:
                    theme["colorBindings"].pop(f"{role_name}.fill", None)
                if not opacity_only and not fidelity_only:
                    theme["colorBindings"][f"{role_name}.glowColor"] = "category:marquee-bulb"
            elif not opacity_only and not fidelity_only:
                theme["colorBindings"][f"{role_name}.glowColor"] = "category:marquee-bulb"
    return parts


def _render(directory: Path, *, parts: dict | None = None, profile: str = SVG, target: str = "svg",
            actual: dict | None = None):
    directory.mkdir(parents=True, exist_ok=True)
    parts = _presentation() if parts is None else parts
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    project = sr.project({"task": sr.span("task", date(2026, 1, 5), 30, title="Synthetic task")})
    project["project"]["title"] = "Glow title"
    draft = resolve_draft_render(
        project_path=sr._write(directory / "project.yaml", project), view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        actual_path=sr._write(directory / "actual.yaml", actual) if actual is not None else None,
        icon_catalog_paths=(_catalogue(directory),), viewport=(900, 560),
        target_kind=target, visual_profile=profile)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=None, draft_auto_block=draft.auto_block))


def _heading_primitives(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.scene_id in {"kicker", "title", "subtitle"}}


def _glyphs(rendered):
    return [item for item in rendered.surface.primitives
            if item.scene_id.startswith("frame-glyph:marquee-title-panel:part")]


def _raster(review, path: Path) -> Image.Image:
    path.write_bytes(review.artifact.content)
    return Image.open(io.BytesIO(review.artifact.content)).convert("RGB")


def _network_parts(*, omit_heading_fill: bool = False) -> dict:
    parts = _presentation(heading_glow=True, frame_glow=False)
    layout = parts["layout"]
    layout["requiredThemeTokens"] = ["spacing.l", "spacing.m"]
    title_slot = sr.find_node(layout, "title")
    layout["root"]["children"] = [title_slot, {
        "id": "network", "kind": "slot", "source": "network", "inlineSize": "fill", "blockSize": "fill",
        "place": {"inline": "stretch", "block": "stretch", "safety": "strict"},
        "priority": "required", "overflow": "visible-overflow",
    }]
    body = parts["view"]["body"]
    body["surface"] = "dependency-network"
    for key in ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "shading",
                "timePresentation", "annotations", "annotationPresentation"):
        body.pop(key, None)
    body["rows"] = {"mode": "automatic"}
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    body["visibility"] = {"labels": False, "relations": "semantic", "annotations": "none"}
    if omit_heading_fill:
        parts["theme"]["body"]["colorBindings"].pop("heading.fill", None)
    return parts


def test_glow_paints_every_heading_and_frame_glyph_in_scene_svg_and_png(tmp_path):
    parts = _presentation(heading_glow=True, frame_glow=True)
    svg_review = _render(tmp_path / "svg", parts=parts)
    png_review = _render(tmp_path / "png", parts=parts, target="png", profile=PNG)
    headings = _heading_primitives(svg_review)
    glyphs = _glyphs(svg_review)

    assert set(headings) == {"kicker", "title", "subtitle"}
    assert all(item.paint.glow is not None and item.paint.glow.color == GLOW_FILL for item in headings.values())
    assert len(glyphs) > 8
    assert {item.visual_role for item in glyphs} == {"frame-glyph-marquee"}
    assert all(item.paint.glow is not None and item.paint.glow.color == GLOW_FILL for item in glyphs)
    assert all(item.paint.glow is not None for item in _glyphs(png_review))
    svg = ET.fromstring(svg_review.artifact.content)
    svg_path = tmp_path / "glowing.svg"
    svg_path.write_bytes(svg_review.artifact.content)
    nodes = {node.attrib.get("data-scene-id"): node for node in svg.iter()}
    parents = {child: parent for parent in svg.iter() for child in parent}
    assert all(nodes[identifier] is not None and
               (parents[nodes[identifier]] if identifier in headings else nodes[identifier]).attrib.get("filter", "").startswith("url(#glow-")
               for identifier in (*headings, *(item.scene_id for item in glyphs)))
    filters = {item.paint.glow.color for item in (*headings.values(), *glyphs)}
    assert filters == {GLOW_FILL}
    title_finding, = [finding for finding in evaluate_scene_contrast(scene_document(svg_review.scene))
                      if finding.primitive_id == "title"]
    assert (title_finding.disposition, title_finding.floor, title_finding.ground_id,
            title_finding.ground_color, title_finding.paint_channel) == (
                "required", 4.5, "region-frame:marquee-title-panel", "#181818", "fill")

    # Actual adapter pixels differ in the halo but not at a distant location;
    # the test keeps both rasters for visual review rather than trusting Scene alone.
    plain = _render(tmp_path / "png-plain", parts=_presentation(), target="png", profile=PNG)
    glowing_image = _raster(png_review, tmp_path / "glow.png")
    plain_image = _raster(plain, tmp_path / "plain.png")
    title = _heading_primitives(png_review)["title"]
    x, y, width, height = title.bounds
    halo_strip = (max(0, round(x + width / 2) - 1), max(0, round(y) - 5),
                  min(glowing_image.width, round(x + width / 2) + 2), min(glowing_image.height, round(y) - 1))
    assert ImageChops.difference(glowing_image.crop(halo_strip), plain_image.crop(halo_strip)).getbbox()
    glyph = _glyphs(png_review)[0]
    glyph_points = [point for command in glyph.symbol.outline for point in command.points]
    left, top = min(point[0] for point in glyph_points), min(point[1] for point in glyph_points)
    right = max(point[0] for point in glyph_points)
    glyph_halo_pixel = (round((left + right) / 2), max(0, round(top) - 5))
    assert glyph_halo_pixel[1] < top
    assert glowing_image.getpixel(glyph_halo_pixel) != plain_image.getpixel(glyph_halo_pixel)
    assert glowing_image.getpixel((glowing_image.width - 2, glowing_image.height - 2)) == \
        plain_image.getpixel((plain_image.width - 2, plain_image.height - 2))


@pytest.mark.parametrize("role", ["heading", "kicker", "subtitle"])
def test_glow_request_requires_its_own_heading_fill(tmp_path, role):
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, parts=_presentation(heading_glow=True, omit_fill=role))
    assert error.value.code == "E_THEME_ROLE_REQUIRED"
    assert error.value.source_ref == f"/body/roles/{role}/fill"


def test_baseline_omits_optional_heading_and_frame_glow_but_keeps_ink(tmp_path):
    review = _render(tmp_path, parts=_presentation(heading_glow=True, frame_glow=True,
                                                   fidelity="decorative-optional"), profile=BASELINE)
    headings = _heading_primitives(review)
    glyphs = _glyphs(review)
    omissions = [item for item in review.info_diagnostics if item.code == "I_VISUAL_TREATMENT_OMITTED"]

    assert all(item.paint.glow is None for item in (*headings.values(), *glyphs))
    assert all(item.paint.fill for item in (*headings.values(), *glyphs))
    assert {item.role for item in omissions} >= {"heading", "kicker", "subtitle", "frame-glyph-marquee"}
    assert b"<filter" not in review.artifact.content
    path = tmp_path / "baseline-optional.svg"
    path.write_bytes(review.artifact.content)
    assert b"Glow title" in review.artifact.content
    svg = ET.fromstring(review.artifact.content)
    scene_ids = {node.attrib.get("data-scene-id") for node in svg.iter()}
    assert {item.scene_id for item in glyphs} <= scene_ids


def test_required_frame_glyph_glow_rejects_baseline_at_its_fidelity_pointer(tmp_path):
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, parts=_presentation(frame_glow=True), profile=BASELINE)
    assert error.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"
    assert error.value.source_ref == "/body/roles/frame-glyph-marquee/glowBlur"


def test_a_lone_glow_opacity_is_still_an_invalid_partial_glow_tuple(tmp_path):
    parts = _presentation(heading_glow=False, frame_glow=False)
    parts["theme"]["body"]["roles"]["heading"]["glowOpacity"] = "test-glow-opacity"
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, parts=parts)
    assert error.value.code == "E_VISUAL_CAPABILITY_VALUE"
    assert error.value.source_ref == "/body/roles/heading/glowBlur"


@pytest.mark.parametrize("variant", ["opacity-only", "fidelity-only"])
def test_opacity_only_and_fidelity_only_leave_default_heading_and_frame_bytes_unchanged(tmp_path, variant):
    plain = _render(tmp_path / "plain", parts=_presentation(heading_glow=False, frame_glow=False))
    if variant == "opacity-only":
        altered = _presentation(heading_glow=True, frame_glow=True, opacity_only=True)
    else:
        altered = _presentation(heading_glow=True, frame_glow=True, fidelity_only=True)
    unchanged = _render(tmp_path / variant, parts=altered)

    assert unchanged.artifact.content == plain.artifact.content
    assert scene_document(unchanged.scene)["surfaces"] == scene_document(plain.scene)["surfaces"]


def test_declared_heading_glow_changes_paint_not_completed_title_geometry(tmp_path):
    plain = _render(tmp_path / "plain", parts=_presentation())
    glowing = _render(tmp_path / "glowing", parts=_presentation(heading_glow=True))
    before, after = _heading_primitives(plain), _heading_primitives(glowing)
    assert set(before) == set(after) == {"kicker", "title", "subtitle"}
    for identifier in before:
        assert (after[identifier].bounds, after[identifier].baseline, after[identifier].text,
                after[identifier].text_layout) == (before[identifier].bounds, before[identifier].baseline,
                                                   before[identifier].text, before[identifier].text_layout)
        assert after[identifier].paint.fill == before[identifier].paint.fill
        assert after[identifier].paint.glow is not None
    assert _glyphs(plain)[0].bounds == _glyphs(glowing)[0].bounds


def test_dependency_network_title_glow_uses_heading_paint_role_and_requires_own_fill(tmp_path):
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-02-20", "observations": []}}
    rendered = _render(tmp_path / "network", parts=_network_parts(), actual=actual)
    title = next(item for item in rendered.surface.primitives if item.scene_id == "title")
    assert title.visual_role == "heading" and title.paint.glow is not None
    root = ET.fromstring(rendered.artifact.content)
    node = next(item for item in root.iter() if item.attrib.get("data-scene-id") == "title")
    assert node.attrib["fill"] == title.paint.fill
    parents = {child: parent for parent in root.iter() for child in parent}
    assert parents[node].attrib["filter"].startswith("url(#glow-")
    assert "filter" not in node.attrib

    with pytest.raises(RenderFailed) as error:
        _render(tmp_path / "network-no-fill", parts=_network_parts(omit_heading_fill=True), actual=actual)
    assert error.value.code == "E_THEME_ROLE_REQUIRED"
    assert error.value.source_ref == "/body/roles/heading/fill"
