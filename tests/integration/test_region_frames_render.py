"""A Layout Profile region frame draws a panel under its region and only when declared and painted (#889).

A small synthetic Project is rendered through packaged preset bundles whose Layout Profile gains framed
containers and whose Theme gains the `region-frame` role. No test reads `examples/`.
"""
from __future__ import annotations

import io
import re
from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
import resvg_py
import yaml
from PIL import Image

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
DOTS = "chrona-target-parts:ben-day-dots"
RICH = "chrona-output/visual/v0.6-svg"
BASELINE = "chrona-output/visual/v0.5-baseline"
FRAMES = ("region-frame:title-panel", "region-frame:review")


def _source() -> dict:
    objects = {}
    for index, owner in enumerate("abc"):
        for step in range(2):
            key = f"{owner}{step}"
            objects[key] = sr.span(key, date(2026, 3, 2) + timedelta(days=index * 9 + step * 50), 40, owner=owner,
                                   title=f"Synthetic task {key}")
    return sr.project(objects)


def _title_panel(title: dict, frame: dict | None) -> dict:
    node = {"id": "title-panel", "kind": "row", "inlineSize": "content", "blockSize": "content",
            "gap": {"token": "spacing.none"}, "padding": {"token": "spacing.m"}, "alignItems": "start",
            "justifyContent": "start", "place": {"inline": "center", "block": "start", "safety": "safe"},
            "children": [title]}
    if frame is not None:
        node["frame"] = frame
    return node


def _presentation(*, bundle: str = "executive-light", frames: bool = True, role: dict | None = None,
                  bindings: dict | None = None, values: dict | None = None, version: str | None = None,
                  fill: str = "neutral") -> dict:
    """The packaged bundle with a framed title panel and chart panel, and the `region-frame` role when `role` is given.

    With `frames=False` the Layout Profile keeps the same containers and paddings and declares no frame, so
    the arrangement is identical and only the declaration differs.
    """
    parts = sr.bundle(bundle)
    if version is not None:
        parts["theme"]["version"] = version
    root = parts["layout"]["root"]
    root["children"][0] = _title_panel(root["children"][0], {"inset": 4} if frames else None)
    review = sr.find_node(parts["layout"], "review")
    review["padding"] = {"token": "spacing.m"}
    if frames:
        review["frame"] = {"inset": 4}
    if role is not None:
        body = parts["theme"]["body"]
        body["values"].update(values or {})
        body["values"].setdefault("frame.width", {"type": "number", "value": 3})
        body["values"].setdefault("frame.radius", {"type": "number", "value": 14})
        body["roles"]["region-frame"] = role
        body["colorBindings"].update({"region-frame.fill": fill, "region-frame.stroke": "text", **(bindings or {})})
        for key in [key for key, value in body["colorBindings"].items() if value is None]:
            del body["colorBindings"][key]  # a None binding declares no such channel
    return parts


ROLE = {"strokeWidth": "frame.width", "frameCornerRadius": "frame.radius"}


def _render(directory: Path, presentation: dict, **options):
    directory.mkdir(parents=True, exist_ok=True)
    return sr.render(directory, _source(), presentation=presentation, **options)


def _frames(review) -> dict:
    return {item.scene_id: item for item in review.surface.primitives if item.visual_role == "region-frame"}


def _png(review, directory: Path) -> Image.Image:
    path = directory / "board.svg"
    path.write_bytes(review.artifact.content)
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_path=str(path), zoom=1, font_dirs=[],
                                                              skip_system_fonts=False)))).convert("RGB")


def test_frames_are_ordinary_rects_emitted_first_in_profile_order_with_their_own_slots(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role=ROLE))
    primitives = review.surface.primitives

    assert [item.scene_id for item in primitives[:2]] == list(FRAMES)
    title, chart = (_frames(review)[name] for name in FRAMES)
    assert (title.kind.value, title.purpose, title.visual_role, title.paint_order) == ("Rect", "region-frame", "region-frame", 0)
    assert title.slot_id == "frame:title-panel" and chart.slot_id == "frame:review"
    assert title.corner_radius == 14 and chart.corner_radius == 14
    assert (title.paint.fill, title.paint.stroke, title.paint.stroke_width) == ("#C9CED8", "#172033", 3.0)
    slots = {item.slot_id: item for item in review.surface.slots}
    assert slots["frame:review"].bounds == chart.bounds and slots["frame:review"].source == "frame:review"
    svg = review.artifact.content.decode()
    rects = re.findall(r'<rect [^>]*data-scene-id="([^"]+)"[^>]*>', svg)
    assert rects[:2] == list(FRAMES)
    assert 'rx="14' in re.search(r'<rect [^>]*data-scene-id="region-frame:review"[^>]*>', svg).group(0)
    assert svg.index("region-frame:review") < svg.index('data-scene-id="title"')


def test_a_frame_paints_below_every_other_primitive_whatever_paint_order_they_declare(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role=ROLE))
    order = [item.scene_id for _index, item in sorted(enumerate(review.surface.primitives),
                                                      key=lambda pair: (pair[1].paint_order, pair[0]))]

    assert order[:2] == list(FRAMES)
    assert min(item.paint_order for item in review.surface.primitives if item.visual_role != "region-frame") >= 0


def test_a_panel_is_the_node_allocation_deflated_by_inset_and_half_the_stroke(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role=ROLE))
    slots = {item.slot_id: item.bounds for item in review.surface.slots}
    table, axis = slots["table"], slots["timeline-axis"]
    chart = _frames(review)["region-frame:review"].bounds

    # The review row is padded by spacing.m and inset by 4 with a 3 px stroke: the panel stands 4 + 1.5 inside the row.
    row_x, row_y = chart[0] - 5.5, chart[1] - 5.5
    assert table[0] == pytest.approx(row_x + 16) and axis[1] == pytest.approx(row_y + 16)
    assert chart[0] + chart[2] + 5.5 == pytest.approx(slots["timeline"][0] + slots["timeline"][2] + 16)


def test_a_declaration_without_the_role_and_a_role_without_a_declaration_each_change_nothing(tmp_path) -> None:
    plain = _render(tmp_path / "plain", _presentation(frames=False))
    declared = _render(tmp_path / "declared", _presentation(frames=True))
    painted = _render(tmp_path / "painted", _presentation(frames=False, role=ROLE))

    assert declared.artifact.content == plain.artifact.content
    assert painted.artifact.content == plain.artifact.content
    assert _frames(declared) == {} and _frames(painted) == {}
    assert not any(slot.slot_id.startswith("frame:") for slot in declared.surface.slots)
    assert not any("REGION_FRAME" in item for item in declared.scene.diagnostics)


def test_a_frame_never_moves_or_clips_content(tmp_path) -> None:
    without = _render(tmp_path / "without", _presentation(frames=False, role=ROLE))
    with_frames = _render(tmp_path / "with", _presentation(frames=True, role=ROLE))

    rest = tuple(item for item in with_frames.surface.primitives if item.visual_role != "region-frame")
    assert rest == without.surface.primitives
    assert tuple(item for item in with_frames.surface.slots if not item.slot_id.startswith("frame:")) == without.surface.slots
    assert with_frames.surface.rows == without.surface.rows
    assert with_frames.surface.columns == without.surface.columns
    assert with_frames.surface.groups == without.surface.groups
    assert with_frames.surface.canvas_bounds == without.surface.canvas_bounds
    assert with_frames.surface.fit_warnings == without.surface.fit_warnings
    assert len(with_frames.surface.primitives) == len(without.surface.primitives) + 2


def test_the_png_shows_the_panel_fill_its_ink_outline_the_gutter_and_the_canvas_around_it(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role=ROLE))
    image = _png(review, tmp_path)
    title, chart = (_frames(review)[name].bounds for name in FRAMES)
    fill, ink, canvas = (0xC9, 0xCE, 0xD8), (0x17, 0x20, 0x33), (255, 255, 255)

    assert image.getpixel((int(chart[0] + chart[2] / 2), int(chart[1] + chart[3] - 40))) == fill  # empty strip in the panel
    assert image.getpixel((int(chart[0] + chart[2] / 2), int(chart[1]))) == ink  # the top edge
    assert image.getpixel((int(chart[0]), int(chart[1] + chart[3] / 2))) == ink  # the left edge
    between = int((title[1] + title[3] + chart[1]) / 2)
    assert image.getpixel((int(chart[0] + chart[2] / 2), between)) == canvas  # the gutter between the panels
    assert image.getpixel((int(chart[0]) - 12, int(chart[1] + chart[3] / 2))) == canvas  # beyond the panel
    # The rounded corner leaves the canvas at the very corner and ink on the arc.
    assert image.getpixel((int(chart[0]) + 1, int(chart[1]) + 1)) == canvas


def test_two_renders_are_byte_identical(tmp_path) -> None:
    first = _render(tmp_path / "a", _presentation(role=ROLE))
    second = _render(tmp_path / "b", _presentation(role=ROLE))

    assert first.artifact.content == second.artifact.content


def test_a_role_with_only_a_stroke_is_an_outline_panel_and_not_ground(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role={"strokeWidth": "frame.width"},
                                             bindings={"region-frame.fill": None}))
    findings = evaluate_scene_contrast(scene_document(review.scene))

    assert all(item.paint.fill is None for item in _frames(review).values())
    assert not [item for item in findings if (item.ground_id or "").startswith("region-frame:")]


def test_a_role_with_neither_fill_nor_stroke_fails_at_its_exact_pointer(tmp_path) -> None:
    parts = _presentation(role={}, bindings={"region-frame.fill": None, "region-frame.stroke": None})
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, parts)

    assert (error.value.code, error.value.source_ref) == ("E_THEME_ROLE_REQUIRED", "/body/roles/region-frame/stroke")


def test_what_lies_on_a_panel_is_gated_against_its_fill(tmp_path) -> None:
    strong = evaluate_scene_contrast(scene_document(_render(tmp_path / "strong", _presentation(role=ROLE, fill="surface")).scene))
    faint = evaluate_scene_contrast(scene_document(_render(
        tmp_path / "faint", _presentation(role=ROLE, fill="accent")).scene), decoration_severity="error")

    on_panel = [item for item in strong if item.ground_id == "region-frame:review"]
    assert on_panel and {item.ground_kind for item in on_panel} == {"flat"}
    assert not [item for item in strong if item.severity == "error"]
    failed = [item for item in faint if item.severity == "error" and item.ground_id == "region-frame:review"]
    assert failed and {item.code for item in failed} <= {"E_SCENE_DECORATION_CONTRAST", "E_SCENE_MARK_CONTRAST", "E_SCENE_STATE_TEXT_CONTRAST"}
    assert all(item.ground_color == "#3986E6" for item in failed)


def test_a_translucent_panel_fill_is_composited_over_the_canvas_beneath_it(tmp_path) -> None:
    values = {"frame.opacity": {"type": "number", "value": 0.5}}
    review = _render(tmp_path, _presentation(role={**ROLE, "opacity": "frame.opacity"}, values=values))
    findings = evaluate_scene_contrast(scene_document(review.scene))

    # Judged on the panel over its canvas (#1013), not refused: no finding is an unreadable ground.
    # A decoration on the panel keeps its warning (decorations are not composited, #995).
    on_panel = [item for item in findings
                if item.ground_id == "region-frame:review" and item.severity_class == "legibility"]
    assert on_panel and {item.ground_kind for item in on_panel} == {"translucent-over-canvas"}
    assert not [item for item in findings if item.code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"]
    assert {item.code for item in findings if item.severity_class == "decoration" and item.severity == "warning"
            and item.ground_id == "region-frame:review"} <= {"W_SCENE_DECORATION_GROUND_UNSUPPORTED"}
    assert all(item.ground_color != "#C9CED8" for item in on_panel)  # the composite, not the panel's own fill


def test_the_serialized_scene_stays_v06_without_a_pattern(tmp_path) -> None:
    assert scene_document(_render(tmp_path, _presentation(role=ROLE)).scene)["version"] == "chrona/scene/v0.6"


def test_a_corner_radius_larger_than_the_panel_allows_is_reduced_and_recorded(tmp_path) -> None:
    values = {"frame.radius": {"type": "number", "value": 4000}}
    review = _render(tmp_path, _presentation(role=ROLE, values=values))
    title = _frames(review)["region-frame:title-panel"]

    assert title.corner_radius == pytest.approx(min(title.bounds[2], title.bounds[3]) / 2)
    assert "W_LAYOUT_REGION_FRAME_CORNER_REDUCED:title-panel" in review.scene.diagnostics
    assert "W_LAYOUT_REGION_FRAME_CORNER_REDUCED:review" in review.scene.diagnostics


def test_a_panel_the_stroke_consumes_is_omitted_and_recorded_without_moving_anything(tmp_path) -> None:
    values = {"frame.width": {"type": "number", "value": 4000}}
    review = _render(tmp_path, _presentation(role=ROLE, values=values))

    assert _frames(review) == {}
    assert "I_LAYOUT_REGION_FRAME_OMITTED:title-panel:too-small" in review.scene.diagnostics
    assert "I_LAYOUT_REGION_FRAME_OMITTED:review:too-small" in review.scene.diagnostics


def _key_panel(parts: dict) -> None:
    """A framed key panel beside the chart panel, holding the optional legend slot."""
    legend = {"id": "legend", "kind": "slot", "source": "legend", "inlineSize": "content", "blockSize": "content",
              "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": "optional",
              "overflow": "visible-overflow"}
    key = {"id": "key-panel", "kind": "row", "inlineSize": "content", "blockSize": "content", "gap": {"token": "spacing.none"},
           "padding": {"token": "spacing.m"}, "alignItems": "start", "justifyContent": "start", "frame": {},
           "place": {"inline": "start", "block": "start", "safety": "safe"}, "children": [legend]}
    parts["layout"]["root"]["children"].insert(1, key)
    parts["layout"]["requiredThemeTokens"] = sorted({*parts["layout"]["requiredThemeTokens"], "spacing.none", "spacing.m"})


def _annotations_panel(parts: dict, *, frame: bool) -> None:
    """Wrap the packaged optional `annotations` slot in a panel; this Project has no annotations, so it is absent."""
    root = parts["layout"]["root"]
    index = next(i for i, child in enumerate(root["children"]) if child["id"] == "annotations")
    panel = {"id": "annotations-panel", "kind": "row", "inlineSize": "content", "blockSize": "content",
             "gap": {"token": "spacing.none"}, "padding": {"token": "spacing.m"}, "alignItems": "start",
             "justifyContent": "start", "place": {"inline": "start", "block": "start", "safety": "safe"},
             "children": [root["children"][index]]}
    if frame:
        panel["frame"] = {}
    root["children"][index] = panel


def test_a_panel_around_an_absent_region_is_not_drawn_and_the_rest_does_not_move(tmp_path) -> None:
    absent = _presentation(role=ROLE)
    _annotations_panel(absent, frame=True)
    review = _render(tmp_path / "absent", absent)

    assert not any(item.slot_id == "annotations" for item in review.surface.slots)
    assert "region-frame:annotations-panel" not in _frames(review)
    assert "I_LAYOUT_REGION_FRAME_OMITTED:annotations-panel:no-content" in review.scene.diagnostics
    assert "frame:annotations-panel" not in {item.slot_id for item in review.surface.slots}
    # Omitting the panel moves nothing: with the declaration removed every other primitive is identical.
    unframed = _presentation(role=ROLE)
    _annotations_panel(unframed, frame=False)
    other = _render(tmp_path / "unframed", unframed)
    assert review.surface.primitives == other.surface.primitives
    assert tuple(item for item in review.surface.slots if not item.slot_id.startswith("frame:")) == tuple(
        item for item in other.surface.slots if not item.slot_id.startswith("frame:"))


def test_a_framed_key_panel_is_drawn_when_its_legend_is_present(tmp_path) -> None:
    parts = _presentation(bundle="control-room-dark", role=ROLE)
    _key_panel(parts)
    objects = {f"t{index}": sr.span(f"t{index}", date(2026, 1, 5 + index), 20, owner=owner)
               for index, owner in enumerate(("assembly-integration-and-test", "ground", "launch-and-range"))}
    review = sr.render(tmp_path, sr.project(objects), presentation=parts)

    key = _frames(review).get("region-frame:key-panel")
    legend = next(item for item in review.surface.slots if item.source == "legend")
    assert key is not None and not any(line.startswith("I_LAYOUT_REGION_FRAME_OMITTED:key-panel") for line in review.scene.diagnostics)
    assert key.bounds[0] < legend.bounds[0] and key.bounds[0] + key.bounds[2] > legend.bounds[0] + legend.bounds[2]
    assert key.bounds[1] < legend.bounds[1] and key.bounds[1] + key.bounds[3] > legend.bounds[1] + legend.bounds[3]


def test_a_frame_around_a_slot_taller_than_its_rows_keeps_the_plot_overlays_ending_at_the_last_row(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role=ROLE))
    chart = _frames(review)["region-frame:review"].bounds
    rows_end = max(item.bounds[1] + item.bounds[3] for item in review.surface.rows)
    overlays = [item for item in review.surface.primitives if item.visual_role in {"axis-major", "axis-minor"}]

    assert chart[1] + chart[3] > rows_end + 100  # the panel is the allocation
    assert overlays and all(max(point[1] for point in item.points) <= rows_end + 1e-6 for item in overlays
                            if item.purpose == "axis-grid")


def test_the_canvas_grows_to_contain_a_frame_that_reaches_past_it(tmp_path) -> None:
    def parts(role: bool) -> dict:
        value = _presentation(frames=False, role=ROLE if role else None)
        wide = {"id": "wide", "kind": "row", "inlineSize": {"fixed": {"token": "wide"}}, "blockSize": "content",
                "gap": {"token": "spacing.none"}, "padding": {"token": "spacing.none"}, "alignItems": "start",
                "justifyContent": "start", "frame": {},
                "place": {"inline": "start", "block": "start", "safety": "strict"}}
        # The title slot moves into the wide container, so the panel is populated and reaches past the canvas.
        title_panel = sr.find_node(value["layout"], "title-panel")
        wide["children"] = title_panel["children"]
        value["layout"]["root"]["children"][0] = wide
        value["layout"]["requiredThemeTokens"] = sorted({*value["layout"]["requiredThemeTokens"], "wide"})
        value["theme"]["body"]["values"]["wide"] = {"type": "number", "value": 2400}
        return value

    grown = _render(tmp_path / "grown", parts(True))
    plain = _render(tmp_path / "plain", parts(False))
    frame = _frames(grown)["region-frame:wide"].bounds

    assert plain.surface.canvas_bounds[2] < 2400
    # The canvas holds the whole stroke, not just the rectangle's centre line.
    assert grown.surface.canvas_bounds[0] + grown.surface.canvas_bounds[2] == pytest.approx(frame[0] + frame[2] + 1.5)


def test_typst_and_tikz_draw_a_plain_frame_with_its_radius(tmp_path) -> None:
    review = _render(tmp_path, _presentation(role=ROLE))

    for render in (render_v05_typst, render_v05_tikz):
        source = render(review.surface)
        assert isinstance(source, str) and "14" in source


def _patterned(directory: Path):
    parts = _presentation(version="chrona/theme/v0.15", role={"frameCornerRadius": "frame.radius", "pattern": "frame.dots"},
                          values={"frame.dots": {"type": "pattern", "value": {"kind": "catalog", "ref": DOTS}}},
                          fill="surface", bindings={"region-frame.stroke": "neutral"})
    return _render(directory, parts, icon_catalogs=(CATALOGUE,))


def test_a_halftone_panel_carries_a_catalogue_pattern_and_typst_and_tikz_reject_it(tmp_path) -> None:
    review = _patterned(tmp_path)
    chart = _frames(review)["region-frame:review"]

    assert chart.pattern is not None and chart.pattern.primitives
    assert scene_document(review.scene)["version"] == "chrona/scene/v0.7"
    assert "<pattern " in review.artifact.content.decode()
    for render in (render_v05_typst, render_v05_tikz):
        with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
            render(review.surface)
    findings = evaluate_scene_contrast(scene_document(review.scene))
    assert not [item for item in findings if item.severity == "error"]


def test_a_panel_below_a_canvas_texture_keeps_the_texture_first(tmp_path) -> None:
    parts = _presentation(version="chrona/theme/v0.15", role=ROLE, values={
        "canvas-texture.lattice": {"type": "pattern", "value": {"kind": "catalog", "ref": "chrona-target-parts:hexagon-lattice"}}},
                          bindings={"canvas-texture.fill": "surface", "canvas-texture.stroke": "surfaceRaised"})
    parts["theme"]["body"]["roles"]["canvas-texture"] = {"pattern": "canvas-texture.lattice"}
    review = _render(tmp_path, parts, icon_catalogs=(CATALOGUE,))

    assert [item.scene_id for item in review.surface.primitives[:3]] == ["canvas-texture", *FRAMES]


def _rich(directory: Path, presentation: dict, profile: str):
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    for kind, value in presentation.items():
        paths[kind] = directory / f"{kind}.yaml"
        paths[kind].write_text(yaml.safe_dump(value, sort_keys=False, allow_unicode=True), encoding="utf-8")
    project = directory / "project.yaml"
    project.write_text(yaml.safe_dump(_source(), sort_keys=False), encoding="utf-8")
    draft = resolve_draft_render(project_path=project, view_path=paths["view"], theme_path=paths["theme"],
                                 scheme_path=paths["scheme"], layout_path=paths["layout"], viewport=(1600, 900),
                                 visual_profile=profile)
    return render_review(RenderRequest(closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
                                       scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(),
                                       draft_auto_block=draft.auto_block))


def test_a_hand_inked_panel_composes_with_the_wobble_and_changes_no_bound(tmp_path) -> None:
    values = {"wobble.amp": {"type": "number", "value": 1.6}, "wobble.wave": {"type": "number", "value": 22},
              "wobble.seed": {"type": "number", "value": 7}}
    role = {**ROLE, "wobbleAmplitude": "wobble.amp", "wobbleWavelength": "wobble.wave", "wobbleSeed": "wobble.seed"}
    wobbly = _rich(tmp_path / "wobbly", _presentation(role=role, values=values), RICH)
    straight = _rich(tmp_path / "straight", _presentation(role=ROLE), RICH)

    for name in FRAMES:
        before, after = _frames(straight)[name], _frames(wobbly)[name]
        assert after.paint.wobble is not None and after.paint.wobble.closed and after.paint.wobble.outline
        assert (after.bounds, after.corner_radius, after.slot_id) == (before.bounds, before.corner_radius, before.slot_id)
    assert wobbly.artifact.content != straight.artifact.content
    assert _rich(tmp_path / "again", _presentation(role=role, values=values), RICH).artifact.content == wobbly.artifact.content
    assert tuple(replace(item, paint=None) for item in wobbly.surface.primitives if item.visual_role != "region-frame") == tuple(
        replace(item, paint=None) for item in straight.surface.primitives if item.visual_role != "region-frame")
