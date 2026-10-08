"""Border-flush annotation-kind bars and bar-end stamps (#1242)."""
from __future__ import annotations

from copy import deepcopy
import io
from math import atan2, degrees, sqrt
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image
import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


SVG = "chrona-output/visual/v0.6-svg"
PNG = "chrona-output/visual/v0.6-png"
INSET = {"top": 0.8, "right": 1.1, "bottom": 0.7, "left": 1.4}
BORDERS = {
    "start": {"width": 4, "paint": "kind"},
    "end": {"width": 7, "paint": "kind"},
    "top": {"width": 5, "paint": "kind"},
    "bottom": {"width": 3, "paint": "kind"},
}


def _parts(*, stamp: bool = False, placement: str = "column", bar_bleed: str | None = None,
           bar_width: str = "fill", corner_radius: float = 0, inset: dict | None = INSET,
           text: str | None = None, borders: bool = True, stamp_size: float = 2.0):
    source = ak.project(("risk",), text=text or "A long annotation body which wraps into multiple lines " * 3)
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts, border_side="start", border_width=BORDERS["start"]["width"],
                       stamp="end-top" if stamp else None, stamp_size=stamp_size)
    theme = parts["theme"]["body"]
    if stamp:
        # Keep the stamp's declared role ink explicit; bar-end preserves this
        # paint instead of inheriting the kind-coloured bar tint.
        theme["colorBindings"]["annotation-kind-stamp.fill"] = "text"
        theme["colorBindings"]["annotation-kind-stamp.stroke"] = "text"
    if bar_bleed is not None:
        theme["roles"]["annotation-kind-bar"]["barBleed"] = bar_bleed
    theme["roles"]["annotation-kind-bar"]["barWidth"] = bar_width
    container_id = theme["roles"]["annotation-note-box"]["annotationContainer"]
    container = theme["values"][container_id]["value"]
    container["cornerRadius"] = corner_radius
    if borders:
        container["border"] = deepcopy(BORDERS)
    else:
        container.pop("border", None)
    if inset is not None:
        container["contentInsetEm"] = deepcopy(inset)
    if stamp:
        stamp_id = theme["roles"]["annotation-kind-stamp"]["stampPlacement"]
        stamp_value = {"placement": placement, "size": stamp_size}
        if placement == "column":
            stamp_value["corner"] = "end-top"
        theme["values"][stamp_id]["value"] = stamp_value
    _separate_heading(parts)
    return source, parts


def _separate_heading(parts):
    theme = parts["theme"]["body"]
    for kind in theme["annotationKinds"].values():
        kind["title"] = "{label} · {secondary}"
        kind["heading"] = "{subject}"
    theme["roles"]["annotation-heading"] = {
        **deepcopy(theme["roles"]["annotation-kind-label"]),
        "fontSize": "kind-heading-size", "lineHeight": "kind-heading-line",
    }
    theme["values"].update({
        "kind-heading-size": {"type": "number", "value": 24},
        "kind-heading-line": {"type": "number", "value": 1.3},
    })
    theme["colorBindings"]["annotation-heading.fill"] = "text"


def _render(directory: Path, *, target: str = "svg", source=None, parts=None):
    directory.mkdir(parents=True, exist_ok=True)
    source = source or ak.project(("risk",), text="A long annotation body which wraps into multiple lines " * 3)
    if parts is None:
        source, parts = _parts()
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    profile = SVG if target == "svg" else PNG
    draft = resolve_draft_render(
        project_path=sr._write(directory / "project.yaml", source), view_path=paths["view"],
        theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"],
        icon_catalog_paths=(ak.TARGET_PARTS,), viewport=(1200, 800), target_kind=target,
        visual_profile=profile)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=None, draft_auto_block=draft.auto_block))


def _ids(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _geometry(rendered, note="view-n0"):
    ids = _ids(rendered)
    return (ids[f"annotation-box:{note}"], ids[f"annotation-kind-bar:{note}"],
            ids[f"annotation-heading:{note}"], ids[f"annotation-text:{note}"])


def _with_explicit_defaults(parts):
    theme = parts["theme"]["body"]
    theme["roles"]["annotation-kind-bar"]["barBleed"] = "none"
    stamp_id = theme["roles"]["annotation-kind-stamp"]["stampPlacement"]
    theme["values"][stamp_id]["value"]["placement"] = "column"


@pytest.mark.parametrize("target", ["svg", "png"])
@pytest.mark.parametrize("bar_width", ["fill", "hug"])
def test_border_bleed_uses_distinct_inner_edges_and_keeps_inset_content_below_bar(tmp_path, target, bar_width):
    source, parts = _parts(stamp=True, placement="bar-end", bar_bleed="border", bar_width=bar_width,
                           corner_radius=0)
    rendered = _render(tmp_path / target, target=target, source=source, parts=parts)
    box, bar, heading, body = _geometry(rendered)
    x, y, width, height = box.bounds
    size = body.text_layout.font_size

    assert bar.bounds[0] == pytest.approx(x + BORDERS["start"]["width"])
    assert bar.bounds[1] == pytest.approx(y + BORDERS["top"]["width"])
    assert bar.bounds[0] + bar.bounds[2] == pytest.approx(x + width - BORDERS["end"]["width"])
    assert bar.bounds[0] >= x and bar.bounds[0] + bar.bounds[2] <= x + width
    assert bar.bounds[1] + bar.bounds[3] <= y + height
    assert heading.bounds[0] >= x + BORDERS["start"]["width"] + INSET["left"] * size - 0.01
    assert body.bounds[0] >= x + BORDERS["start"]["width"] + INSET["left"] * size - 0.01
    assert heading.bounds[1] >= bar.bounds[1] + bar.bounds[3] + INSET["top"] * size - 0.01
    assert body.bounds[1] >= heading.bounds[1] + heading.bounds[3] - 0.01
    assert len(body.text_layout.lines) > 1

    if target == "svg":
        nodes = {node.attrib.get("data-scene-id"): node for node in ET.fromstring(rendered.artifact.content).iter()}
        assert nodes[bar.scene_id] is not None and nodes[heading.scene_id] is not None
        svg_bar = nodes[bar.scene_id]
        assert float(svg_bar.attrib["x"]) == pytest.approx(bar.bounds[0])
        assert float(svg_bar.attrib["y"]) == pytest.approx(bar.bounds[1])
        assert float(svg_bar.attrib["width"]) == pytest.approx(bar.bounds[2])
        assert float(svg_bar.attrib["height"]) == pytest.approx(bar.bounds[3])
        (tmp_path / f"{target}-bleed.svg").write_bytes(rendered.artifact.content)
    else:
        assert rendered.artifact.target_kind == "png"
        image = Image.open(io.BytesIO(rendered.artifact.content)).convert("RGB")
        (tmp_path / f"{target}-bleed.png").write_bytes(rendered.artifact.content)
        assert image.width > 0 and image.height > 0
        sample = image.getpixel((round(bar.bounds[0] + bar.bounds[2] / 2), round(bar.bounds[1] + 2)))
        assert sample == (142, 27, 18)


@pytest.mark.parametrize("bar_width", ["fill", "hug"])
def test_border_bleed_keeps_rounded_corner_content_clearance_and_square_corner_strip(tmp_path, bar_width):
    source, parts = _parts(bar_bleed="border", bar_width=bar_width, corner_radius=0.8,
                           inset={"top": 0, "right": 0, "bottom": 0, "left": 0}, borders=False)
    rendered = _render(tmp_path, target="png", source=source, parts=parts)
    box, bar, heading, body = _geometry(rendered)
    x, y, width, _ = box.bounds
    radius = box.corner_radius
    assert radius > 0
    # Bleed follows the inner-border rectangle. Text retains the rounded-box
    # clearance even when the declared content inset is smaller than it.
    assert bar.bounds[:3] == pytest.approx((x, y, width))
    clearance = radius * (1 - 1 / sqrt(2))
    assert heading.bounds[0] - x >= clearance - 0.01
    assert body.bounds[0] - x >= clearance - 0.01
    assert heading.bounds[1] - y >= clearance - 0.01
    image = Image.open(io.BytesIO(rendered.artifact.content)).convert("RGB")
    # The approved bleed is a square-ended strip; rounded-corner clearance is
    # retained for content, but no rounded cutout is applied to the bar.
    assert image.getpixel((round(x + 1), round(y + 1))) == (142, 27, 18)


@pytest.mark.parametrize("bar_width", ["fill", "hug"])
def test_bar_end_stamp_is_centred_at_the_bar_end_without_a_body_column(tmp_path, bar_width):
    source, plain_parts = _parts(bar_bleed="border", text="A repeatable body phrase for line breaking. " * 6)
    plain = _render(tmp_path / "plain", source=source, parts=plain_parts)
    source, stamped_parts = _parts(stamp=True, placement="bar-end", bar_bleed="border", bar_width=bar_width,
                                   text="A repeatable body phrase for line breaking. " * 6)
    stamped = _render(tmp_path / "stamped", source=source, parts=stamped_parts)
    plain_box, plain_bar, plain_heading, plain_body = _geometry(plain)
    box, bar, heading, body = _geometry(stamped)
    stamp = _ids(stamped)["annotation-kind-stamp:view-n0:part0"]

    assert stamp.bounds[0] + stamp.bounds[2] == pytest.approx(bar.bounds[0] + bar.bounds[2])
    assert stamp.bounds[1] >= bar.bounds[1] - 0.01
    assert stamp.bounds[1] + stamp.bounds[3] <= bar.bounds[1] + bar.bounds[3] + 0.01
    assert stamp.bounds[1] + stamp.bounds[3] / 2 == pytest.approx(bar.bounds[1] + bar.bounds[3] / 2)
    gap = 0.5 * body.text_layout.font_size
    labels = [item for item in _ids(stamped).values()
              if item.scene_id.startswith("annotation-kind-text:view-n0:")]
    assert labels
    for label in labels:
        assert label.bounds[0] + label.bounds[2] <= stamp.bounds[0] - gap + 0.01
    assert body.bounds[0] - box.bounds[0] == pytest.approx(plain_body.bounds[0] - plain_box.bounds[0])
    assert body.bounds[1] - box.bounds[1] == pytest.approx(plain_body.bounds[1] - plain_box.bounds[1])
    assert body.text_layout.lines == plain_body.text_layout.lines
    assert heading.bounds[0] - box.bounds[0] == pytest.approx(plain_heading.bounds[0] - plain_box.bounds[0])
    # The filled bar may grow for the stamp, but no stamp column shifts the content origin.
    assert bar.bounds[0] == pytest.approx(plain_bar.bounds[0])


def test_bar_end_preserves_a_wide_glyph_aspect_and_grows_bar_for_an_oversized_stamp(tmp_path):
    source, parts = _parts(stamp=True, placement="bar-end", bar_bleed="border")
    theme = parts["theme"]["body"]
    theme["annotationKinds"]["risk"]["stamp"] = "chrona-target-parts:hazard-tab"
    stamp_id = theme["roles"]["annotation-kind-stamp"]["stampPlacement"]
    theme["values"][stamp_id]["value"]["size"] = 4.5
    rendered = _render(tmp_path, source=source, parts=parts)
    _, bar, _, _ = _geometry(rendered)
    stamp = _ids(rendered)["annotation-kind-stamp:view-n0:part0"]
    assert stamp.bounds[0] + stamp.bounds[2] == pytest.approx(bar.bounds[0] + bar.bounds[2])
    assert stamp.bounds[2] / stamp.bounds[3] == pytest.approx(56 / 24)
    assert bar.bounds[3] >= stamp.bounds[3]


@pytest.mark.parametrize("bar_width", ["fill", "hug"])
def test_nonbleeding_bar_end_uses_no_body_column_and_keeps_its_declared_gap(tmp_path, bar_width):
    source, parts = _parts(stamp=True, placement="bar-end", bar_width=bar_width,
                           text="A short body.", stamp_size=1.5)
    rendered = _render(tmp_path, source=source, parts=parts)
    ids = _ids(rendered)
    bar, body = ids["annotation-kind-bar:view-n0"], ids["annotation-text:view-n0"]
    stamp = ids["annotation-kind-stamp:view-n0:part0"]
    gap = 0.5 * body.text_layout.font_size

    assert stamp.bounds[0] + stamp.bounds[2] == pytest.approx(bar.bounds[0] + bar.bounds[2])
    assert stamp.bounds[1] + stamp.bounds[3] / 2 == pytest.approx(bar.bounds[1] + bar.bounds[3] / 2)
    labels = [item for item in ids.values() if item.scene_id.startswith("annotation-kind-text:view-n0:")]
    assert labels
    for label in labels:
        assert label.bounds[0] + label.bounds[2] <= stamp.bounds[0] - gap + 0.01
    assert body.bounds[0] == pytest.approx(ids["annotation-box:view-n0"].bounds[0]
                                           + BORDERS["start"]["width"] + INSET["left"] * body.text_layout.font_size)


@pytest.mark.parametrize("target", ["svg", "png"])
def test_bar_end_stamp_keeps_its_declared_role_ink_in_both_adapters(tmp_path, target):
    source, parts = _parts(stamp=True, placement="bar-end", bar_bleed="border")
    rendered = _render(tmp_path, target=target, source=source, parts=parts)
    ids = _ids(rendered)
    bar = ids["annotation-kind-bar:view-n0"]
    body = ids["annotation-text:view-n0"]
    stamp_parts = [item for item in rendered.surface.primitives
                   if item.scene_id.startswith("annotation-kind-stamp:view-n0:")]
    assert stamp_parts and bar.paint.fill == ak.KIND_COLORS["kind-alert"]
    declared_fill = body.paint.fill
    declared_stroke = body.paint.fill
    assert declared_fill != bar.paint.fill
    assert {paint for item in stamp_parts for paint in (item.paint.fill, item.paint.stroke) if paint} == {
        declared_fill, declared_stroke}

    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    stamp_findings = [finding for finding in findings
                      if finding.primitive_id in {item.scene_id for item in stamp_parts}]
    assert stamp_findings
    assert all(finding.ground_id == bar.scene_id and finding.ground_color == bar.paint.fill
               and finding.disposition == "enabled" and finding.severity != "none"
               for finding in stamp_findings)

    if target == "svg":
        path = tmp_path / "bar-end-role-paint.svg"
        path.write_bytes(rendered.artifact.content)
        nodes = {node.attrib.get("data-scene-id"): node for node in ET.fromstring(rendered.artifact.content).iter()}
        glyph_nodes = [nodes[item.scene_id] for item in stamp_parts]
        inks = {node.attrib.get(channel) for node in glyph_nodes for channel in ("fill", "stroke")
                if node.attrib.get(channel) not in (None, "none")}
        assert inks == {declared_fill, declared_stroke}
    else:
        path = tmp_path / "bar-end-role-paint.png"
        path.write_bytes(rendered.artifact.content)
        image = Image.open(io.BytesIO(rendered.artifact.content)).convert("RGB")
        stamp = stamp_parts[0]
        left, top, width, height = stamp.bounds
        crop = image.crop((max(0, round(left)), max(0, round(top)),
                           min(image.width, round(left + width)), min(image.height, round(top + height))))
        assert crop.width > 0 and crop.height > 0
        expected = tuple(int(declared_stroke[index:index + 2], 16) for index in (1, 3, 5))
        assert any(sum(abs(actual - wanted) for actual, wanted in zip(pixel, expected)) < 24
                   for pixel in crop.get_flattened_data())


def test_tilted_border_bleed_bar_and_bar_end_stamp_share_local_frame(tmp_path):
    angle = 6.0
    source, parts = _parts(stamp=True, placement="bar-end", bar_bleed="border", borders=False,
                           corner_radius=0)
    ak.with_tilt(parts, [angle])
    rendered = _render(tmp_path, source=source, parts=parts)
    ids = _ids(rendered)
    box, bar = ids["annotation-box:view-n0"], ids["annotation-kind-bar:view-n0"]
    stamp_parts = [item for item in rendered.surface.primitives
                   if item.scene_id.startswith("annotation-kind-stamp:view-n0:")]
    assert stamp_parts

    box_corners = [command.points[0] for command in box.symbol.outline[:4]]
    bar_corners = [command.points[0] for command in bar.symbol.outline[:4]]
    assert bar_corners[0] == pytest.approx(box_corners[0], abs=1e-3)
    edge = (bar_corners[1][0] - bar_corners[0][0], bar_corners[1][1] - bar_corners[0][1])
    inline_length = sqrt(edge[0] ** 2 + edge[1] ** 2)
    u = (edge[0] / inline_length, edge[1] / inline_length)
    v = (-u[1], u[0])
    assert degrees(atan2(u[1], u[0])) == pytest.approx(angle, abs=1e-3)

    # Project the actual completed stamp outlines back into the bar's local
    # frame; axis-aligned bounds are too loose for rotated shapes.
    points = [point for item in stamp_parts for command in item.symbol.outline for point in command.points]
    assert points
    local = []
    origin = bar_corners[0]
    for x, y in points:
        dx, dy = x - origin[0], y - origin[1]
        local.append((dx * u[0] + dy * u[1], dx * v[0] + dy * v[1]))
    bar_height = abs((bar_corners[3][0] - origin[0]) * v[0]
                     + (bar_corners[3][1] - origin[1]) * v[1])
    assert min(x for x, _ in local) >= -0.01
    assert max(x for x, _ in local) <= inline_length + 0.01
    assert min(y for _, y in local) >= -0.01
    assert max(y for _, y in local) <= bar_height + 0.01

    body = ids["annotation-text:view-n0"]
    assert {paint for item in stamp_parts for paint in (item.paint.fill, item.paint.stroke) if paint} == {
        body.paint.fill}
    svg = ET.fromstring(rendered.artifact.content)
    nodes = {node.attrib.get("data-scene-id"): node for node in svg.iter()}
    assert all(nodes[item.scene_id] is not None for item in stamp_parts)
    assert all(nodes[item.scene_id].attrib.get("fill") == body.paint.fill
               or nodes[item.scene_id].attrib.get("stroke") == body.paint.fill for item in stamp_parts)


def test_missing_drawable_bar_reports_the_owning_annotation_for_bar_end_stamp(tmp_path):
    source, parts = _parts(stamp=True, placement="bar-end", bar_bleed="border")
    theme = parts["theme"]["body"]
    del theme["roles"]["annotation-kind-bar"]
    del theme["colorBindings"]["annotation-kind-bar.fill"]
    for role in ("annotation-kind-label", "annotation-kind-secondary"):
        theme["colorBindings"][f"{role}.fill"] = "text"
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, source=source, parts=parts)
    assert caught.value.code == "E_LAYOUT_ANNOTATION_KIND_STAMP_PLACEMENT"
    assert caught.value.source_ref == "/annotations/0"
    assert "requires a drawable annotation-kind label bar" in caught.value.message


def test_absent_and_explicit_none_column_defaults_keep_scene_and_svg_bytes(tmp_path):
    source, absent_parts = _parts(stamp=True, placement="column", bar_bleed=None)
    absent = _render(tmp_path / "absent", source=source, parts=absent_parts)
    source, explicit_parts = _parts(stamp=True, placement="column", bar_bleed=None)
    _with_explicit_defaults(explicit_parts)
    explicit = _render(tmp_path / "explicit", source=source, parts=explicit_parts)

    assert list(absent.surface.primitives) == list(explicit.surface.primitives)
    assert scene_document(absent.scene)["surfaces"] == scene_document(explicit.scene)["surfaces"]
    assert absent.artifact.content == explicit.artifact.content
