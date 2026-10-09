"""#585 I585-2: a vertical group label spanning its rows, rendered end to end.

A Theme `writingMode: vertical` on the `groupHeader` role moves each group label into a tag column carved from the
table's start; Layout completes the label as per-segment Text. Synthetic Projects through the packaged
`executive-light` bundle (Latin, always) and, where the optional package is installed, Noto Sans JP (CJK).
No `examples/` input.
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
import resvg_py
from PIL import Image, ImageChops

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

SIZE = 22
FONTS = [*sorted((tt.ROOT / "src/chrona/resources/fonts").glob("*.ttf")),
         *sorted((tt.ROOT / "packages/chrona-fonts-noto-cjk/src/chrona_fonts_noto_cjk/fonts").glob("*.ttf"))]
needs_cjk = pytest.mark.skipif(not tt.cjk_available(), reason="requires the optional chrona-fonts-noto-cjk package")


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _render(tmp_path, *, vertical=True, cjk=False, header_text=None, mutate=None, presentation=None):
    source = sr.bunched_project(groups=3, per_group=3)
    parts = sr.bundle()
    if presentation is not None:
        parts["view"]["body"]["grouping"]["presentation"] = presentation
    if vertical:
        tt.with_vertical_groups(parts, size=SIZE, header_text=header_text, family=tt.JP if cjk else None)
    if mutate is not None:
        mutate(parts)
    return tt.render(tmp_path, source, parts, cjk=cjk)


def _tags(rendered, group="team-0"):
    return [item for scene_id, item in sorted(tt.texts(rendered).items()) if scene_id.startswith(f"group-tag:{group}:")]


def _group_rows(rendered, group):
    cells = [item for key, item in tt.texts(rendered).items() if key.startswith("cell:") and f'"{group}"' in key and key.endswith(":Lane")]
    return min(item.bounds[1] for item in cells), max(item.bounds[1] + item.bounds[3] for item in cells)


def test_declaring_horizontal_or_nothing_is_the_default_output(tmp_path):
    base = _render(_sub(tmp_path, "base"), vertical=False)
    horizontal = _render(_sub(tmp_path, "horizontal"), vertical=False,
                         mutate=lambda parts: tt.with_vertical_groups(parts, mode="horizontal"))
    assert horizontal.artifact.content == base.artifact.content
    assert list(horizontal.surface.primitives) == list(base.surface.primitives)
    assert not [key for key in tt.texts(base) if key.startswith("group-tag:")]


def test_the_label_becomes_per_segment_text_in_a_column_at_the_tables_start(tmp_path):
    base = _render(_sub(tmp_path, "base"), vertical=False)
    vertical = _render(_sub(tmp_path, "vertical"))
    assert not [key for key in tt.texts(vertical) if key.startswith("group-header:")]  # no horizontal label remains
    tags = _tags(vertical)
    assert tags and all(item.purpose == "group-header" for item in tags)
    line = float(sr.bundle()["theme"]["body"]["values"][sr.bundle()["theme"]["body"]["roles"]["groupHeader"]["lineHeight"]]["value"])
    column = SIZE * line  # the role's line box: fontSize x lineHeight
    table_start = min(item.bounds[0] for key, item in tt.texts(base).items() if key.startswith("cell:"))
    for item in tags:
        assert item.bounds[0] >= table_start - 1e-6 and item.bounds[0] + item.bounds[2] <= table_start + column + 1e-6
    # The table's columns start exactly one column later.
    first_cell = lambda rendered: min(item.bounds[0] for key, item in tt.texts(rendered).items() if key.startswith("cell:"))
    assert first_cell(vertical) - first_cell(base) == pytest.approx(column, abs=1e-6)


def test_each_tag_spans_its_groups_rows_and_stays_inside_them(tmp_path):
    vertical = _render(_sub(tmp_path, "vertical"))
    for group in ("team-0", "team-1", "team-2"):
        tags = _tags(vertical, group)
        top, bottom = _group_rows(vertical, group)
        assert tags[0].bounds[1] >= top - 1e-6 and tags[-1].bounds[1] + tags[-1].bounds[3] <= bottom + 1e-6, group
        assert tags[0].bounds[1] > top  # half an em of clear space at the start
        spans = [(item.bounds[1], item.bounds[1] + item.bounds[3]) for item in tags]
        assert all(second[0] >= first[1] - 1e-6 for first, second in zip(spans, spans[1:]))  # no overlap


def test_the_header_row_is_not_reserved(tmp_path):
    base = _render(_sub(tmp_path, "base"), vertical=False)
    vertical = _render(_sub(tmp_path, "vertical"))
    assert not any(item.scene_id.startswith("group-header-band") for item in vertical.surface.primitives)
    first = lambda rendered: min(item.bounds[1] for key, item in tt.texts(rendered).items() if key.startswith("cell:"))
    assert first(vertical) < first(base)  # the rows start where the first header row used to


def test_a_content_sized_canvas_counts_no_header_rows_for_vertical_labels(tmp_path):
    """The required block extent is computed before layout; with vertical labels it must not include header rows."""
    def canvas_slack(rendered):
        rows = [item for key, item in tt.texts(rendered).items() if key.startswith("cell:")]
        return rendered.surface.canvas_bounds[3] - max(item.bounds[1] + item.bounds[3] for item in rows)

    def render(name, vertical, block=None):
        parts = sr.bundle()
        if vertical:
            tt.with_vertical_groups(parts, size=SIZE)
        return tt.render(_sub(tmp_path, name), sr.bunched_project(groups=3, per_group=3), parts, viewport=(1600, block))

    base, vertical = render("base", False), render("vertical", True)
    # A fixed viewport too small for the rows grows to the same minimum as the content-sized canvas does.
    assert render("small", True, 440).surface.canvas_bounds[3] == vertical.surface.canvas_bounds[3]
    assert vertical.surface.canvas_bounds[3] < base.surface.canvas_bounds[3]
    assert canvas_slack(vertical) == pytest.approx(canvas_slack(base), abs=1e-6)  # no block extent is left over


def test_a_band_presentation_has_no_labels_and_is_unaffected(tmp_path):
    base = _render(_sub(tmp_path, "base"), vertical=False, presentation="band")
    vertical = _render(_sub(tmp_path, "vertical"), presentation="band")
    assert vertical.artifact.content == base.artifact.content


def test_a_latin_run_is_a_quarter_turn_clockwise_and_reads_top_to_bottom(tmp_path):
    vertical = _render(_sub(tmp_path, "vertical"))
    tags = _tags(vertical)
    assert [item.text for item in tags][0].startswith("Team")
    assert {item.text_layout.orientation for item in tags if item.text.isascii() and item.text != "…"} == {"rotate-cw"}
    assert all(item.text_layout.rotation_degrees == 90 for item in tags if item.text_layout.orientation == "rotate-cw")
    text = tags[0]
    x, y = text.baseline
    assert text.bounds[1] == pytest.approx(y)  # the run starts at its baseline origin and runs down


def test_the_tags_pass_the_perceptibility_gate_and_a_collision_would_be_caught(tmp_path):
    vertical = _render(_sub(tmp_path, "vertical"))
    document = scene_document(vertical.scene)
    assert not [item for item in evaluate_scene_perceptibility(document) if item.severity == "error"]
    primitives = {item["id"]: item for item in document["surfaces"][0]["primitives"]}
    first, second = "group-tag:team-0:0", "group-tag:team-0:1"
    assert first in primitives and second in primitives
    primitives[second]["bounds"] = dict(primitives[first]["bounds"])
    errors = [item for item in evaluate_scene_perceptibility(document) if item.code == "E_SCENE_TEXT_INTERSECTION"]
    assert errors and any({first, second} <= set(item.primitive_ids) for item in errors)


def test_typst_and_tikz_draw_the_segments_as_ordinary_quarter_turn_text(tmp_path):
    surface = _render(_sub(tmp_path, "vertical")).surface
    assert "#rotate(90deg" in render_v05_typst(surface)
    assert "rotate=90" in render_v05_tikz(surface)


def test_a_horizontal_scale_on_a_vertical_role_is_a_typed_conflict(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, mutate=lambda parts: tt.with_scale(parts, ("groupHeader",), 0.8))
    assert "E_THEME_TEXT_TREATMENT_CONFLICT" in str(failure.value) + repr(getattr(failure.value, "__cause__", ""))
    # The same scale on the horizontal role is fine, so the conflict is the combination's.
    assert _render(_sub(tmp_path, "ok"), vertical=False, mutate=lambda parts: tt.with_scale(parts, ("groupHeader",), 0.8))


def test_a_role_that_does_not_support_a_writing_mode_is_rejected_by_the_existing_diagnostic(tmp_path):
    def on_text(parts):
        parts["theme"]["body"]["values"]["wm"] = {"type": "writingMode", "value": "vertical"}
        parts["theme"]["body"]["roles"]["text"]["writingMode"] = "wm"

    with pytest.raises(Exception) as failure:
        _render(tmp_path, vertical=False, mutate=on_text)
    assert "E_THEME_ROLE_PROPERTY_UNSUPPORTED" in str(failure.value) + repr(getattr(failure.value, "__cause__", ""))


def test_a_writing_mode_value_other_than_horizontal_or_vertical_is_rejected(tmp_path):
    with pytest.raises(Exception):
        _render(tmp_path, vertical=False, mutate=lambda parts: tt.with_vertical_groups(parts, mode="diagonal"))


def test_rendering_twice_gives_the_same_bytes(tmp_path):
    assert _render(_sub(tmp_path, "a")).artifact.content == _render(_sub(tmp_path, "b")).artifact.content


def _png(rendered):
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(
        svg_string=rendered.artifact.content.decode(), font_files=[str(path) for path in FONTS],
        skip_system_fonts=True)))).convert("RGB")


def _ink(image, box):
    x0, y0, x1, y1 = (int(round(value)) for value in box)
    crop = image.crop((x0, y0, x1, y1))
    difference = ImageChops.difference(crop, Image.new("RGB", crop.size, crop.getpixel((0, 0)))).convert("L")
    return difference.point(lambda value: 255 if value > 60 else 0).getbbox()


def test_the_png_draws_each_latin_segment_inside_its_bounds_and_turned_clockwise(tmp_path):
    rendered = _render(tmp_path)
    image = _png(rendered)
    run = next(item for item in _tags(rendered) if item.text.startswith("Team"))
    x, y, w, h = run.bounds
    box = _ink(image, (x - 2, y - 2, x + w + 2, y + h + 2))
    assert box is not None
    ink_w, ink_h = box[2] - box[0], box[3] - box[1]
    assert ink_h > 2 * ink_w  # the word runs down the column, it is not laid out across it
    assert ink_h <= h + 4  # and does not run past its measured extent


@needs_cjk
def test_cjk_stands_upright_one_em_per_character_and_latin_turns_sideways(tmp_path):
    rendered = _render(tmp_path, cjk=True, header_text="機体・{title}")
    tags = _tags(rendered)
    upright = [item for item in tags if item.text_layout.orientation == "horizontal"]
    assert [item.text for item in upright[:3]] == ["機", "体", "・"]
    assert all(item.bounds[3] == pytest.approx(SIZE) for item in upright)  # one em per character
    assert all(item.text_layout.rotation_degrees == 0 for item in upright)
    blocks = [item.bounds[1] for item in upright[:3]]
    assert blocks[1] - blocks[0] == pytest.approx(SIZE) and blocks[2] - blocks[1] == pytest.approx(SIZE)
    sideways = [item for item in tags if item.text_layout.orientation == "rotate-cw"]
    assert sideways and all(item.text.isascii() or item.text == "…" for item in sideways)  # Latin and the ellipsis turn sideways
    assert all(item.text_layout.family.startswith("Noto Sans JP") for item in tags)


@needs_cjk
def test_the_png_draws_the_cjk_characters_in_their_cells(tmp_path):
    rendered = _render(tmp_path, cjk=True, header_text="機体・{title}")
    image = _png(rendered)
    for item in [item for item in _tags(rendered) if item.text in {"機", "体"}]:
        x, y, w, h = item.bounds
        box = _ink(image, (x - 1, y - 1, x + w + 1, y + h + 1))
        assert box is not None and (box[2] - box[0]) > 0.5 * SIZE and (box[3] - box[1]) > 0.5 * SIZE, item.text  # a glyph, in its cell


# --- #981: truncation is reported; a short tag can be aligned ----------------------------------------------

SHORT = "{ordinal}"
LONG = "An exceptionally long programme group title that cannot fit its rows"


def _align(value):
    def mutate(parts):
        parts["theme"]["body"]["roles"]["groupHeader"]["align"] = value
    return mutate


def test_a_tag_cut_to_its_rows_is_reported_with_its_source(tmp_path):
    rendered = _render(tmp_path, header_text=LONG)
    warnings = [item for item in rendered.surface.fit_warnings if item.failure_kind == "group-tag-text"]

    assert {item.source_ref for item in warnings} == {"team-0", "team-1", "team-2"}
    assert all(item.code == "W_LAYOUT_TEXT_ELLIPSIZED" and item.behaviour == "ellipsize-with-source"
               and item.required_block > item.available_block for item in warnings)
    assert all(item.placement_id.startswith("group-tag:") for item in warnings)


def test_a_tag_that_fits_reports_nothing(tmp_path):
    rendered = _render(tmp_path, header_text=SHORT)

    assert not [item for item in rendered.surface.fit_warnings if item.failure_kind == "group-tag-text"]


def test_align_places_a_short_tag_at_the_start_the_middle_or_the_end_of_its_rows(tmp_path):
    starts = {}
    for name in ("start", "center", "end"):
        rendered = _render(_sub(tmp_path, name), header_text=SHORT, mutate=_align(name))
        tags = _tags(rendered)
        top, bottom = _group_rows(rendered, "team-0")
        starts[name] = (tags[0].bounds[1] - top, bottom - (tags[-1].bounds[1] + tags[-1].bounds[3]))

    assert starts["center"][0] == pytest.approx(starts["center"][1], abs=1e-6)
    assert starts["start"][0] < starts["center"][0] < starts["end"][0]


def test_without_align_the_tag_is_start_aligned_as_before(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), header_text=SHORT)
    start = _render(_sub(tmp_path, "start"), header_text=SHORT, mutate=_align("start"))

    assert plain.artifact.content == start.artifact.content


def test_align_on_a_horizontal_group_header_is_refused(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, vertical=False, mutate=_align("end"))

    assert "E_THEME_ROLE_PROPERTY_UNSUPPORTED" in str(failure.value) + repr(getattr(failure.value, "__cause__", ""))
