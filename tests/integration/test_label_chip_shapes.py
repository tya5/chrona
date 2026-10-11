"""Synthetic full-pipeline evidence for non-rectangular label chips (#1286)."""
from __future__ import annotations

from datetime import date
from dataclasses import replace
from hashlib import sha256
from html import escape
from math import cos, pi, sin, sqrt
from pathlib import Path
import re

import pytest
import yaml

from chrona.presentation.scene.serialization import serialize_scene
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis


ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}


def _asof_parts(shape=None, *, label="TODAY!", catalog_stroke=False, numeric_spacing=None):
    parts = use_legacy_six_tier_axis(sr.bundle("executive-light"))
    theme = parts["theme"]["body"]
    if numeric_spacing is not None:
        # Exercise a treatment supported by the existing Theme grammar, not a
        # test-only measurement override.  The as-of run contains digits in
        # its generated date suffix.
        typography = theme["roles"]["text"]
        theme["roles"]["as-of-label"] = {
            name: typography[name] for name in (
                "fontFamily", "fontWeight", "fontSize", "lineHeight", "letterSpacing", "textTransform")
        }
        theme["roles"]["as-of-label"]["numericSpacing"] = numeric_spacing
    role = {"backgroundTreatment": "fill", "chipPadding": "chip-padding"}
    if shape is not None:
        theme["values"]["synthetic-chip-shape"] = {"type": "chipShape", "value": shape}
        role["chipShape"] = "synthetic-chip-shape"
    theme["roles"]["as-of-label-chip"] = role
    theme["colorBindings"]["as-of-label-chip.fill"] = "surfaceRaised"
    if catalog_stroke:
        theme["colorBindings"]["as-of-label-chip.stroke"] = "text"
    marker = next(item for item in parts["view"]["body"]["markers"] if item["kind"] == "asOf")
    marker.update(placement="below-plot", label=label, date={"form": "day-month-year"})
    return parts


def _source():
    return sr.project({
        "alpha": sr.span("alpha", date(2026, 2, 2), 35, title="Alpha synthetic task"),
        "beta": sr.span("beta", date(2026, 2, 5), 28, owner="b", title="Beta synthetic task"),
    })


def _render_asof(directory, shape=None, *, label="TODAY!", catalogs=(), viewport=(1200, 760),
                 catalog_stroke=False, numeric_spacing=None):
    directory.mkdir(parents=True, exist_ok=True)
    return sr.render(directory, _source(), presentation=_asof_parts(shape, label=label,
        catalog_stroke=catalog_stroke, numeric_spacing=numeric_spacing), actual=ACTUAL,
                     viewport=viewport, icon_catalogs=tuple(catalogs))


def _primitive(rendered, scene_id):
    return next(item for item in rendered.surface.primitives if item.scene_id == scene_id)


def _path_data(svg, scene_id):
    match = re.search(rf'<path\b(?=[^>]*data-scene-id="{re.escape(escape(scene_id, quote=True))}")[^>]*\bd="([^"]+)"', svg)
    return match.group(1) if match else None


def _svg_path_points(path):
    commands = re.findall(r"([ML])\s*([-+]?(?:\d+\.?\d*|\.\d+))\s+([-+]?(?:\d+\.?\d*|\.\d+))", path)
    assert commands and "".join(match.group(0) for match in re.finditer(
        r"[ML]\s*[-+]?(?:\d+\.?\d*|\.\d+)\s+[-+]?(?:\d+\.?\d*|\.\d+)", path)) == path
    return tuple((command, float(x), float(y)) for command, x, y in commands)


def _assert_svg_matches_outline(path, outline):
    actual = _svg_path_points(path)
    expected = tuple(("M" if command.kind == "move" else "L", *command.points[0])
                     for command in outline)
    assert len(actual) == len(expected)
    for (actual_command, actual_x, actual_y), (expected_command, expected_x, expected_y) in zip(actual, expected):
        assert actual_command == expected_command
        assert actual_x == pytest.approx(expected_x, abs=0.00051)
        assert actual_y == pytest.approx(expected_y, abs=0.00051)


def _distance_to_segment(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    amount = 0 if length_squared == 0 else max(0, min(1, (
        (point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared))
    nearest = (start[0] + amount * dx, start[1] + amount * dy)
    return ((point[0] - nearest[0]) ** 2 + (point[1] - nearest[1]) ** 2) ** .5


def test_asof_burst_is_completed_symbol_text_fits_and_svg_uses_same_closed_path(tmp_path):
    points, ratio = 9, .48
    rendered = _render_asof(tmp_path / "burst", {"kind": "burst", "points": points,
                                                   "innerRatio": ratio})
    chip = _primitive(rendered, "chip:as-of-label")
    label = _primitive(rendered, "as-of-label")
    assert chip.kind == "Symbol" and chip.symbol is not None
    assert chip.purpose == "label-chip"
    assert label.kind == "Text" and label.text.endswith("TODAY! 20 Feb 2026")

    commands = chip.symbol.outline
    path = _path_data(rendered.artifact.content.decode("utf-8"), chip.scene_id)
    assert path
    _assert_svg_matches_outline(path, commands)
    svg_points = _svg_path_points(path)
    vertices = tuple((x, y) for command, x, y in svg_points[:-1])
    assert len(vertices) == 2 * points
    assert commands[-1].kind == "line" and commands[-1].points[0] == vertices[0]
    cx = sum(x for x, _ in vertices) / len(vertices)
    cy = sum(y for _, y in vertices) / len(vertices)
    radii = tuple(((x - cx) ** 2 + (y - cy) ** 2) ** .5 for x, y in vertices)
    outer = max(radii)
    assert min(radii) / outer == pytest.approx(ratio, abs=1e-3)

    # The chip's text-safe rectangle is its paired text bounds. All four text
    # corners must be inside the polygon's inscribed disk, not merely its box.
    x, y, width, height = label.text_layout.bounds
    inscribed_radius = min(
        _distance_to_segment((cx, cy), a, b)
        for a, b in zip(vertices, (*vertices[1:], vertices[0]))
    )
    for corner_x in (x, x + width):
        for corner_y in (y, y + height):
            assert ((corner_x - cx) ** 2 + (corner_y - cy) ** 2) ** .5 <= inscribed_radius + 1e-3

    svg = rendered.artifact.content.decode("utf-8")
    assert path.count("L") == 2 * points
    assert "<rect" not in svg[svg.find(f'data-scene-id="{chip.scene_id}"') - 20:
                               svg.find(f'data-scene-id="{chip.scene_id}"') + 80]
    assert all(not _overlaps(chip.bounds, other.bounds) for other in rendered.surface.primitives
               if other.scene_id not in {chip.scene_id, label.scene_id, "as-of"}
               and (other.kind == "Text" or other.source_kind == "object"))
    assert not any(warning.identity.startswith("W_LAYOUT_LABEL_SUPPRESSED:as-of-label")
                   for warning in rendered.warning_records)


def test_ellipse_burst_contains_twenty_character_label_in_scene_and_actual_svg(tmp_path):
    points, ratio = 8, .8
    shape = {"kind": "burst", "points": points, "innerRatio": ratio, "fit": "ellipse"}
    parts = _asof_parts(shape, label="ABCDEFGH")
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL, viewport=(1200, 760))
    chip = _primitive(rendered, "chip:as-of-label")
    label = _primitive(rendered, "as-of-label")
    assert chip.kind == "Symbol" and chip.symbol is not None
    assert label.kind == "Text" and label.text == "ABCDEFGH 20 Feb 2026"
    assert len(label.text) == 20

    svg = rendered.artifact.content.decode("utf-8")
    path = _path_data(svg, chip.scene_id)
    assert path
    _assert_svg_matches_outline(path, chip.symbol.outline)
    emitted = _svg_path_points(path)
    vertices = tuple((x, y) for _command, x, y in emitted[:-1])
    center = (sum(x for x, _y in vertices) / len(vertices),
              sum(y for _x, y in vertices) / len(vertices))
    theta = pi / points
    factor = (ratio if ratio <= cos(theta) else
              ratio * sin(theta) / sqrt(1 + ratio * ratio - 2 * ratio * cos(theta)))
    expected_a = max(abs(px - center[0]) for px, _py in vertices)
    expected_b = max(abs(py - center[1]) for _px, py in vertices)
    x, y, width, height = label.text_layout.bounds
    pad_inline = (parts["theme"]["body"]["values"]["chip-padding"]["value"] *
                  label.text_layout.font_size)
    pad_block = pad_inline / 2
    # Scene bounds are the nominal vertex envelope; padding keeps the text
    # rectangle centered within the completed shape.
    assert chip.bounds[0] == pytest.approx(min(px for px, _py in vertices), abs=.001)
    assert chip.bounds[1] == pytest.approx(min(py for _px, py in vertices), abs=.001)
    assert chip.bounds[2] == pytest.approx(max(px for px, _py in vertices) - chip.bounds[0], abs=.001)
    assert chip.bounds[3] <= sqrt(2) / factor * (height + 2 * pad_block) + 1e-3
    for corner_x in (x - pad_inline, x + width + pad_inline):
        for corner_y in (y - pad_block, y + height + pad_block):
            normalized = ((corner_x - center[0]) / expected_a) ** 2 + (
                (corner_y - center[1]) / expected_b) ** 2
            # The chosen true inradius factor is preserved under affine scale.
            assert normalized <= factor * factor + 1e-6
            assert _point_in_polygon((corner_x, corner_y), vertices)
    assert label.bounds[1] >= chip.bounds[1]
    assert label.bounds[1] + label.bounds[3] <= chip.bounds[1] + chip.bounds[3]


def _point_in_polygon(point, vertices):
    inside = False
    for start, end in zip(vertices, (*vertices[1:], vertices[0])):
        if _distance_to_segment(point, start, end) <= 1e-3:
            return True
        if (start[1] > point[1]) != (end[1] > point[1]):
            crossing_x = start[0] + ((point[1] - start[1]) * (end[0] - start[0]) /
                                     (end[1] - start[1]))
            if point[0] < crossing_x:
                inside = not inside
    return inside


def test_default_burst_fit_keeps_circle_outline_and_svg_bytes(tmp_path):
    implicit = _render_asof(tmp_path / "implicit",
                            {"kind": "burst", "points": 7, "innerRatio": .6})
    explicit = _render_asof(tmp_path / "explicit",
                            {"kind": "burst", "points": 7, "innerRatio": .6, "fit": "circle"})
    old_chip = _primitive(implicit, "chip:as-of-label")
    explicit_chip = _primitive(explicit, "chip:as-of-label")
    assert old_chip.bounds == explicit_chip.bounds
    assert old_chip.symbol == explicit_chip.symbol
    assert implicit.artifact.content == explicit.artifact.content


def test_absent_shape_preserves_frozen_pre_feature_scene_and_svg_bytes(tmp_path):
    # Independent unchanged-input rendering of public parent 127392c4, recorded
    # in the #1286 acceptance review. No provenance/geometry normalization.
    rendered = _render_asof(tmp_path)
    scene = serialize_scene(rendered.scene)
    assert len(scene) == 22949
    assert sha256(scene).hexdigest() == "4898941430be3208a167abae1dd19f5910dd9c34699e2b157e4d150570ebb0b2"  # the Scene provenance pins the Theme bytes: only this hash moved with the preset Theme (#946); the SVG hash below did not
    assert len(rendered.artifact.content) == 6992
    assert sha256(rendered.artifact.content).hexdigest() == "74bf8d570ca05067f0000a3002520bb237113b11ac682e21ae367ec0e82c3e0b"


def test_absent_shape_and_explicit_rectangle_are_scene_and_svg_byte_identical(tmp_path):
    absent = _render_asof(tmp_path / "absent")
    explicit = _render_asof(tmp_path / "rectangle", {"kind": "rectangle"})
    assert absent.scene.provenance != explicit.scene.provenance
    assert serialize_scene(replace(explicit.scene, provenance=absent.scene.provenance)) == serialize_scene(absent.scene)
    assert absent.artifact.content == explicit.artifact.content
    assert sha256(absent.artifact.content).digest() == sha256(explicit.artifact.content).digest()


def test_nonrect_chip_retains_text_follows_box_in_actual_svg(tmp_path):
    parts = _asof_parts({"kind": "burst", "points": 7, "innerRatio": .7})
    parts["theme"]["body"]["roles"]["as-of-label-chip"]["viewerFit"] = "text-follows-box"
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL, viewport=(1200, 760))
    chip = _primitive(rendered, "chip:as-of-label")
    label = _primitive(rendered, "as-of-label")
    assert chip.kind == "Symbol"
    assert label.text_layout.fit.mode == "text-follows-box"
    svg = rendered.artifact.content.decode("utf-8")
    assert _path_data(svg, chip.scene_id)
    text = re.search(rf'<text\b(?=[^>]*data-scene-id="{re.escape(label.scene_id)}")[^>]*>', svg)
    assert text and 'textLength="' in text.group(0)


def _multipart_catalogue(path):
    catalogue = yaml.safe_load(CATALOGUE.read_text(encoding="utf-8"))
    catalogue["body"]["glyphs"]["synthetic-chip-frame"] = {
        "viewport": {"inlineSize": 100, "blockSize": 100},
        "parts": [
            {"paint": "fill", "data": "M0 0L50 0L50 100L0 100Z"},
            {"paint": "fill", "data": "M50 0L100 0L100 100L50 100Z"},
            {"paint": "fill", "data": "M45 45L55 45L55 55L45 55Z"},
        ],
    }
    path.write_text(yaml.safe_dump(catalogue, sort_keys=False), encoding="utf-8")
    return path


def _overlaps(left, right):
    return (max(left[0], right[0]) < min(left[0] + left[2], right[0] + right[2]) and
            max(left[1], right[1]) < min(left[1] + left[3], right[1] + right[3]))


def test_catalog_chip_projects_each_nine_slice_part_and_preserves_part_order(tmp_path):
    catalogue = _multipart_catalogue(tmp_path / "catalogue.yaml")
    rendered = _render_asof(
        tmp_path / "catalog", {"kind": "catalog", "glyph": "chrona-target-parts:synthetic-chip-frame",
                               "sliceInsets": {"top": 0, "right": 0, "bottom": 0, "left": 0},
                               "unitEm": .4}, catalogs=(catalogue,), catalog_stroke=True,
    )
    chip_parts = [item for item in rendered.surface.primitives
                  if item.scene_id == "chip:as-of-label" or item.scene_id.startswith("chip:as-of-label:part")]
    assert len(chip_parts) == 3
    assert all(item.kind == "Symbol" and item.symbol is not None for item in chip_parts)
    svg = rendered.artifact.content.decode("utf-8")
    for item in chip_parts:
        path = _path_data(svg, item.scene_id)
        assert path
        _assert_svg_matches_outline(path, item.symbol.outline)
    assert [item.scene_id for item in chip_parts] == [
        "chip:as-of-label", "chip:as-of-label:part1", "chip:as-of-label:part2"]
    svg_order = [svg.index(f'data-scene-id="{item.scene_id}"') for item in chip_parts]
    assert svg_order == sorted(svg_order)
    assert all(item.paint.fill and item.paint.stroke is None for item in chip_parts)


@pytest.mark.parametrize("fit", ["circle", "ellipse"])
def test_member_label_lane_chip_keeps_each_label_attached_to_its_own_row(tmp_path, fit):
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body["roles"]["member-label-chip"] = {
        "backgroundTreatment": "fill", "chipPadding": "chip-padding",
        "chipShape": "member-chip-shape",
    }
    body["values"]["member-chip-shape"] = {
        "type": "chipShape", "value": {"kind": "burst", "points": 7, "innerRatio": .7, "fit": fit}}
    body["colorBindings"]["member-label-chip.fill"] = "surfaceRaised"
    parts["view"] = sr.lane_view(parts["view"], table=True)
    parts["view"]["body"]["visibility"]["labels"]["content"] = ["title"]
    source = sr.project({
        "alpha": sr.span("alpha", date(2026, 2, 2), 4, title="A", owner="a"),
        "beta": sr.span("beta", date(2026, 4, 9), 4, title="B", owner="a"),
    })
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1600, 900))
    labels = [item for item in rendered.surface.primitives if item.kind == "Text" and item.purpose == "member-label"]
    assert {item.source_ref for item in labels} >= {"alpha", "beta"}
    for label in labels:
        chip = _primitive(rendered, f"chip:{label.scene_id}")
        assert chip.kind == "Symbol"
        assert chip.source_ref == label.source_ref
        assert chip.slot_id == label.slot_id
        assert chip.lane_row_id == label.lane_row_id
        assert chip.lane_member_id == label.lane_member_id
        assert chip.paint_order < label.paint_order
        svg_path = _path_data(rendered.artifact.content.decode("utf-8"), chip.scene_id)
        assert svg_path
        _assert_svg_matches_outline(svg_path, chip.symbol.outline)


def test_below_plot_reservation_tracks_the_completed_long_asof_chip(tmp_path):
    shape = {"kind": "burst", "points": 7, "innerRatio": .45}
    short = _render_asof(tmp_path / "short", shape, label="TODAY!", viewport=(1200, None))
    long = _render_asof(tmp_path / "long", shape, label="TODAY! PLEASE REVIEW", viewport=(1200, None))

    def geometry(rendered, label_text):
        chip = _primitive(rendered, "chip:as-of-label")
        label = _primitive(rendered, "as-of-label")
        timeline = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
        footer = next(slot for slot in rendered.surface.slots if slot.source == "group-details")
        rows_bottom = max(row.bounds[1] + row.bounds[3] for row in rendered.surface.rows)
        assert label.text.endswith(f"{label_text} 20 Feb 2026")
        assert chip.bounds[1] == pytest.approx(rows_bottom + 3.5)
        assert chip.bounds[1] + chip.bounds[3] <= footer.bounds[1]
        assert not any(warning.identity.startswith("W_LAYOUT_LABEL_SUPPRESSED:as-of-label")
                       for warning in rendered.warning_records)
        assert all(not _overlaps(chip.bounds, mark.bounds) for mark in rendered.surface.primitives
                   if mark.source_kind == "object")
        return chip, timeline, footer

    short_chip, short_timeline, short_footer = geometry(short, "TODAY!")
    long_chip, long_timeline, long_footer = geometry(long, "TODAY! PLEASE REVIEW")
    assert long_chip.bounds[3] > short_chip.bounds[3]
    assert long_timeline.bounds[3] - short_timeline.bounds[3] == pytest.approx(
        long_chip.bounds[3] - short_chip.bounds[3], abs=1)
    assert long_footer.bounds[1] - short_footer.bounds[1] == pytest.approx(
        long_chip.bounds[3] - short_chip.bounds[3], abs=1)


def test_tabular_asof_text_is_measured_inside_nonrect_chip_and_reserved_before_rows(tmp_path):
    shape = {"kind": "burst", "points": 7, "innerRatio": .45}
    proportional = _render_asof(tmp_path / "proportional", shape, label="REVIEW",
                                 viewport=(1200, None), numeric_spacing="numeric-spacing")
    tabular = _render_asof(tmp_path / "tabular", shape, label="REVIEW",
                           viewport=(1200, None), numeric_spacing="tabular-spacing")

    def facts(rendered):
        chip = _primitive(rendered, "chip:as-of-label")
        label = _primitive(rendered, "as-of-label")
        timeline = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
        footer = next(slot for slot in rendered.surface.slots if slot.source == "group-details")
        rows_bottom = max(row.bounds[1] + row.bounds[3] for row in rendered.surface.rows)
        x, y, width, height = label.text_layout.bounds
        cx, cy, chip_width, chip_height = chip.bounds
        assert cx <= x and cy <= y
        assert cx + chip_width >= x + width
        assert cy + chip_height >= y + height
        assert chip.kind == "Symbol" and label.text_layout.numeric_spacing in {"proportional", "tabular"}
        svg = rendered.artifact.content.decode("utf-8")
        outline = _svg_path_points(_path_data(svg, chip.scene_id))
        vertices = tuple((px, py) for _command, px, py in outline[:-1])
        center = (sum(px for px, _py in vertices) / len(vertices),
                  sum(py for _px, py in vertices) / len(vertices))
        inradius = min(_distance_to_segment(center, start, end)
                       for start, end in zip(vertices, (*vertices[1:], vertices[0])))
        assert all(((px - center[0]) ** 2 + (py - center[1]) ** 2) ** .5 <= inradius + 1e-3
                   for px in (x, x + width) for py in (y, y + height))
        text_tag = re.search(rf'<text\b(?=[^>]*data-scene-id="{re.escape(label.scene_id)}")[^>]*>', svg)
        assert text_tag
        baseline = re.search(r'\bx="([^"]+)"[^>]*\by="([^"]+)"', text_tag.group(0))
        assert baseline
        assert float(baseline.group(1)) == pytest.approx(label.text_layout.baseline[0], abs=.001)
        assert float(baseline.group(2)) == pytest.approx(label.text_layout.baseline[1], abs=.001)
        assert chip.bounds[1] == pytest.approx(rows_bottom + 3.5)
        assert chip.bounds[1] + chip.bounds[3] <= footer.bounds[1]
        return chip, label, timeline, footer

    proportional_chip, proportional_label, proportional_timeline, proportional_footer = facts(proportional)
    tabular_chip, tabular_label, tabular_timeline, tabular_footer = facts(tabular)
    assert proportional_label.text_layout.numeric_spacing == "proportional"
    assert tabular_label.text_layout.numeric_spacing == "tabular"
    assert tabular_label.text_layout.bounds[2] > proportional_label.text_layout.bounds[2]
    # The burst grows in both axes to contain its measured text. Its completed
    # block footprint is what the pre-row reserve must consume.
    assert tabular_chip.bounds[3] > proportional_chip.bounds[3]
    assert proportional_timeline.bounds[3] - tabular_timeline.bounds[3] == pytest.approx(
        tabular_chip.bounds[3] - proportional_chip.bounds[3], abs=1)
    assert tabular_footer.bounds[1] - proportional_footer.bounds[1] == pytest.approx(
        tabular_chip.bounds[3] - proportional_chip.bounds[3], abs=1)


def test_burst_chip_fill_is_the_asof_text_contrast_ground(tmp_path):
    shape = {"kind": "burst", "points": 7, "innerRatio": .45}
    readable = _asof_parts(shape)
    readable["theme"]["body"]["contrastPolicy"] = {"groundText": "error"}
    (tmp_path / "readable").mkdir()
    control = sr.render(tmp_path / "readable", _source(), presentation=readable, actual=ACTUAL,
                        viewport=(1200, 760))
    assert control.artifact.content

    unreadable = _asof_parts(shape)
    theme = unreadable["theme"]["body"]
    theme["colorBindings"]["as-of-label-chip.fill"] = "text"
    theme["contrastPolicy"] = {"groundText": "error"}
    (tmp_path / "same-ink").mkdir()
    with pytest.raises(RenderFailed) as raised:
        sr.render(tmp_path / "same-ink", _source(), presentation=unreadable, actual=ACTUAL,
                  viewport=(1200, 760))
    assert raised.value.code == "E_SCENE_STATE_TEXT_CONTRAST"
    assert raised.value.source_ref == "/body/contrastPolicy/groundText"
    assert "as-of-label" in raised.value.message
