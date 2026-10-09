"""A generic profile frame paints catalogue glyphs through real adapters (#888)."""
from __future__ import annotations

import io
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
import yaml
from PIL import Image

from chrona.presentation.model.closure import resolve_draft_render
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
FIXTURE = ROOT / "tests/fixtures/surface-decoration/marquee-glyph-frame.yaml"
SVG = "chrona-output/visual/v0.6-svg"
PNG = "chrona-output/visual/v0.6-png"
BASELINE = "chrona-output/visual/v0.5-baseline"


def _parts(*, frame: bool = True, role: bool = True, glyph_role: bool = True,
           fidelity: str = "required") -> dict:
    parts = sr.bundle("executive-light")
    node = deepcopy(yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["layoutNode"])
    if not frame:
        node.pop("frame")
    parts["layout"]["root"]["children"][0] = node
    if role:
        patch = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["themePatch"]
        theme = parts["theme"]["body"]
        parts["theme"]["version"] = patch["version"]
        theme["values"].update(deepcopy(patch["values"]))
        theme["values"]["marquee.fidelity"]["value"] = fidelity
        theme["roles"]["region-frame-marquee"] = deepcopy(patch["roles"]["region-frame-marquee"])
        theme["colorBindings"].update({key: value for key, value in patch["colorBindings"].items()
                                       if not key.startswith("frame-glyph-marquee.")})
        if glyph_role:
            theme["roles"]["frame-glyph-marquee"] = deepcopy(patch["roles"]["frame-glyph-marquee"])
            theme["colorBindings"].update({key: value for key, value in patch["colorBindings"].items()
                                           if key.startswith("frame-glyph-marquee.")})
        scheme_patch = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))["schemePatch"]
        parts["scheme"]["body"]["categories"].update(deepcopy(scheme_patch["categories"]))
    return parts


def _render(directory: Path, *, target: str = "svg", profile: str = SVG,
            frame: bool = True, role: bool = True, glyph_role: bool = True,
            fidelity: str = "required"):
    directory.mkdir(parents=True, exist_ok=True)
    parts = _parts(frame=frame, role=role, glyph_role=glyph_role, fidelity=fidelity)
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 30, title="Synthetic task")})
    source["project"]["title"] = "Marquee bulbs"
    draft = resolve_draft_render(
        project_path=sr._write(directory / "project.yaml", source), view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        icon_catalog_paths=(CATALOGUE,), viewport=(900, 560), target_kind=target, visual_profile=profile)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=None, draft_auto_block=draft.auto_block))


def _glyphs(rendered):
    return [item for item in rendered.surface.primitives if item.scene_id.startswith("frame-glyph:marquee-title-panel:part")]


@pytest.mark.parametrize(("target", "profile"), [("svg", SVG), ("png", PNG)])
def test_generic_marquee_frame_renders_real_catalogue_glyph_ink_through_svg_and_png(tmp_path, target, profile):
    rendered = _render(tmp_path / target, target=target, profile=profile)
    glyphs = _glyphs(rendered)

    assert rendered.artifact.target_kind == target
    assert len(glyphs) > 8
    assert all(item.visual_role == "frame-glyph-marquee" and item.source_ref == "layout-node:marquee-title-panel"
               for item in glyphs)
    assert {item.kind.value for item in glyphs} == {"Symbol"}
    assert any(item.paint.fill == "#FFDA63" for item in glyphs)
    assert any(item.paint.stroke == "#C99824" for item in glyphs)
    frame_slot = next(item for item in rendered.surface.slots if item.slot_id == "frame-glyph-slot:marquee-title-panel")
    title = next(item for item in rendered.surface.primitives if item.scene_id == "title")
    assert title.paint.fill == "#F6ECCB"
    assert frame_slot.source == frame_slot.slot_id
    assert all(item.slot_id == frame_slot.slot_id for item in glyphs)
    assert max(item.paint_order for item in glyphs) < title.paint_order
    if target == "svg":
        payload = rendered.artifact.content.decode("utf-8")
        assert 'data-scene-id="frame-glyph:marquee-title-panel:part0"' in payload
        assert "#FFDA63" in payload and "#C99824" in payload
        (tmp_path / f"{target}-marquee.svg").write_text(payload, encoding="utf-8")
        fonts = ROOT / "src/chrona/resources/fonts"
        font_files = [str(fonts / name) for name in (
            "noto-sans-regular-v1.ttf", "noto-sans-bold-v1.ttf", "noto-sans-mono-regular-v1.ttf")]
        png = __import__("resvg_py").svg_to_bytes(
            svg_string=payload, dpi=96, font_files=font_files, skip_system_fonts=True)
    else:
        assert rendered.artifact.media_type == "image/png"
        png = rendered.artifact.content
        (tmp_path / f"{target}-marquee.png").write_bytes(png)
    image = Image.open(io.BytesIO(bytes(png))).convert("RGB")
    image.save(tmp_path / f"{target}-marquee.png")
    colors = set(image.get_flattened_data())
    assert (255, 218, 99) in colors
    assert (246, 236, 203) in colors  # the title is rendered, not just the decorative border
    assert min(sum(abs(actual - expected) for actual, expected in zip(color, (201, 152, 36)))
               for color in colors) < 36


def test_absent_frame_glyph_role_is_byte_identical_to_absent_frame_declaration(tmp_path):
    no_frame = _render(tmp_path / "no-frame", frame=False, role=False)
    absent_role = _render(tmp_path / "absent-role", frame=True, role=False)

    assert absent_role.artifact.content == no_frame.artifact.content
    assert not _glyphs(absent_role)
    assert not any(item.slot_id.startswith("frame-glyph-slot:") for item in absent_role.surface.slots)


def test_decorative_optional_omits_the_whole_frame_and_required_names_the_paint_binding(tmp_path):
    plain = _render(tmp_path / "plain", profile=BASELINE, glyph_role=False)
    omitted = _render(tmp_path / "optional", profile=BASELINE, fidelity="decorative-optional")
    assert not _glyphs(omitted)
    assert omitted.artifact.content == plain.artifact.content
    reports = [item for item in omitted.info_diagnostics if getattr(item, "treatment", None) == "frame-glyph"]
    assert len(reports) == 1
    assert reports[0].role == "frame-glyph-marquee"
    assert reports[0].source_ref == "/body/roles/frame-glyph-marquee/artworkFidelity"

    with pytest.raises(RenderFailed) as failure:
        _render(tmp_path / "required", profile=BASELINE, fidelity="required")
    assert failure.value.code == "E_VISUAL_CAPABILITY_UNSUPPORTED"
    assert failure.value.source_ref == "/body/roles/frame-glyph-marquee/artworkFidelity"
