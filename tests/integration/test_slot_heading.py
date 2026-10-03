"""A slot heading: a caption over a Layout Profile slot and the block it reserves (#1064), end to end.

Synthetic Projects with notes go through the packaged `executive-light` bundle with a 300 px note rail placed beside
the timeline (the arrangement a programme board uses); no test reads `examples/`. The committed Controller Z slide is
evidence, not a gate.
"""
from __future__ import annotations

import io
from copy import deepcopy
from datetime import date

import pytest
import resvg_py
from PIL import Image

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr

RAIL = 300
DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail", "body": {"legend": [
    {"role": "planned", "label": "Planned"}, {"role": "actual", "label": "Actual"}]}}
TARGETS = ["g0-t1", "g1-t2", "g2-t1"]
HEADING = "slot-heading:annotations"


def _rail_candidate():
    return sr.candidate("rail", region={"kind": "slot", "source": "annotations"}, search_kind="row-aligned",
                        connector="leader")


def _beside_the_timeline(parts) -> None:
    """Move the annotations slot into the review row, after the timeline stack: a rail beside the axis band."""
    layout = parts["layout"]
    root = layout["root"]
    node = next(child for child in root["children"] if child["id"] == "annotations")
    root["children"].remove(node)
    node["place"] = {"inline": "stretch", "block": "stretch", "safety": "strict"}
    sr.find_node(layout, "review")["children"].append(node)


def _filled_notes(parts) -> None:
    """Note boxes that take the rail's inline size, so every note sits in the rail (#1051)."""
    body = parts["theme"]["body"]
    body["values"]["note-container"] = {"type": "annotationContainer",
                                         "value": {"outline": "rectangle", "cornerRadius": 0, "inlineSize": "fill"}}
    body["roles"]["annotation-note-box"]["annotationContainer"] = "note-container"


def _with_heading_role(parts, *, colour: str = "textMuted", size: int = 11, transform: str = "uppercase") -> None:
    body = parts["theme"]["body"]
    body["values"].update({
        "slot-heading-size": {"type": "number", "value": size},
        "slot-heading-weight": {"type": "fontWeight", "value": 700},
        "slot-heading-spacing": {"type": "number", "value": 0.1},
        "slot-heading-transform": {"type": "textTransform", "value": transform}})
    body["roles"]["slot-heading"] = {
        **body["roles"]["text"], "fontWeight": "slot-heading-weight", "fontSize": "slot-heading-size",
        "letterSpacing": "slot-heading-spacing", "textTransform": "slot-heading-transform"}
    body["colorBindings"]["slot-heading.fill"] = colour


def _render(tmp_path, *, heading=None, name="r", beside=True, role=True, notes=True, rail=RAIL, configure=None,
            viewport=(1600, 900), colour="textMuted", detail=None, preset="executive-light"):
    directory = tmp_path / name
    directory.mkdir()
    parts = sr.bundle(preset)
    sr.with_note_rail(parts, rail)
    _filled_notes(parts)
    if beside:
        _beside_the_timeline(parts)
    if role:
        _with_heading_role(parts, colour=colour)
    if heading is not None:
        sr.find_node(parts["layout"], "annotations")["heading"] = heading
    if configure is not None:
        configure(parts)
    source = sr.chain_project()
    if notes:
        sr.add_notes(source, parts["view"], TARGETS, [_rail_candidate()], words=3)
    return sr.render(directory, source, presentation=parts, viewport=viewport, detail=detail)


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _slot(rendered, slot_id):
    return next(slot for slot in rendered.surface.slots if slot.slot_id == slot_id)


def _bottom(bounds) -> float:
    return bounds[1] + bounds[3]


def _inside(inner, outer, tolerance=0.01) -> bool:
    return (inner[0] >= outer[0] - tolerance and inner[1] >= outer[1] - tolerance
            and inner[0] + inner[2] <= outer[0] + outer[2] + tolerance
            and inner[1] + inner[3] <= outer[1] + outer[3] + tolerance)


NOTE_PREFIXES = ("annotation-box:", "annotation-text:", "annotation-kind:", "note-index:")


def _rail_content(rendered):
    return [item for item in rendered.surface.primitives if item.slot_id == "annotations"
            and item.scene_id != HEADING and item.scene_id.startswith(NOTE_PREFIXES)]


def test_a_slot_with_a_heading_emits_one_text_with_the_declared_role_inside_the_slot(tmp_path):
    rendered = _render(tmp_path, heading={"text": "Notes"})
    headings = [item for item in rendered.surface.primitives if item.scene_id.startswith("slot-heading:")]
    assert [item.scene_id for item in headings] == [HEADING]  # B1: exactly one
    heading = headings[0]
    assert heading.kind == "Text" and heading.visual_role == "slot-heading" and heading.purpose == "slot-heading"
    assert heading.text == "NOTES"  # the Theme role's text transform styles the profile's copy
    assert heading.slot_id == "annotations"
    assert _inside(heading.bounds, _slot(rendered, "annotations").bounds)
    assert not any("W_SCENE_TEXT_SLOT_ESCAPE" in line for line in rendered.surface.diagnostics)


def test_header_row_places_the_caption_in_the_axis_header_band_and_notes_start_below_it(tmp_path):
    rendered = _render(tmp_path, heading={"text": "Notes", "block": "header-row"})
    heading, axis = _by_id(rendered)[HEADING], _slot(rendered, "timeline-axis")
    assert heading.bounds[1] >= axis.bounds[1] - 0.01 and _bottom(heading.bounds) <= _bottom(axis.bounds) + 0.01  # B2
    assert heading.bounds[1] + heading.bounds[3] / 2 == pytest.approx(axis.bounds[1] + axis.bounds[3] / 2, abs=0.5)
    content = _rail_content(rendered)
    assert content and all(item.bounds[1] >= _bottom(heading.bounds) - 0.01 for item in content)  # B3
    assert min(item.bounds[1] for item in content) >= _bottom(axis.bounds) - 0.01  # the content starts under the band


def test_top_puts_the_caption_at_the_slot_start_and_the_content_moves_down_by_the_reserved_block(tmp_path):
    plain = _render(tmp_path, name="plain")
    headed = _render(tmp_path, heading={"text": "Notes", "block": "top"}, name="headed")
    slot, heading = _slot(headed, "annotations"), _by_id(headed)[HEADING]
    assert heading.bounds[1] == pytest.approx(slot.bounds[1])
    assert slot.bounds == _slot(plain, "annotations").bounds  # the slot keeps its full allocation
    reserved = heading.bounds[3] + 0.5 * 11  # the line box and half a font size
    plain_top = min(item.bounds[1] for item in _rail_content(plain))
    headed_top = min(item.bounds[1] for item in _rail_content(headed))
    assert headed_top >= slot.bounds[1] + reserved - 0.01  # B3: nothing lies under the caption
    assert headed_top >= plain_top - 0.01
    assert all(item.bounds[1] >= _bottom(heading.bounds) - 0.01 for item in _rail_content(headed))


def test_header_row_without_an_axis_band_beside_the_slot_falls_back_to_top_with_a_record(tmp_path):
    rendered = _render(tmp_path, heading={"text": "Notes", "block": "header-row"}, beside=False)
    slot, heading = _slot(rendered, "annotations"), _by_id(rendered)[HEADING]
    assert heading.bounds[1] == pytest.approx(slot.bounds[1])
    assert "I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW:annotations" in rendered.surface.diagnostics


@pytest.mark.parametrize("align", ["start", "center", "end"])
def test_align_positions_the_caption_within_the_slot(tmp_path, align):
    rendered = _render(tmp_path, heading={"text": "Notes", "align": align})
    slot, heading = _slot(rendered, "annotations").bounds, _by_id(rendered)[HEADING]
    expected = {"start": slot[0], "center": slot[0] + (slot[2] - heading.bounds[2]) / 2,
                "end": slot[0] + slot[2] - heading.bounds[2]}[align]
    # The painted width is the transformed text's: compare the baseline origin with a width tolerance.
    assert heading.baseline[0] == pytest.approx(expected, abs=heading.bounds[2] * 0.2 + 0.5)
    if align == "start":
        assert heading.baseline[0] == pytest.approx(slot[0])
    else:
        assert heading.baseline[0] > slot[0] + 1


def test_a_caption_wider_than_the_slot_is_cut_with_its_source_kept(tmp_path):
    rendered = _render(tmp_path, heading={"text": "A very long caption for a narrow rail " * 2})
    heading = _by_id(rendered)[HEADING]
    assert heading.text.endswith("…") and _inside(heading.bounds, _slot(rendered, "annotations").bounds, 0.5)
    assert [record.payload["placementId"] for record in rendered.warning_records
            if record.payload["code"] == "W_LAYOUT_TEXT_ELLIPSIZED"] == [HEADING]


def test_a_slot_too_short_for_its_caption_draws_none_and_reserves_nothing(tmp_path):
    def short(parts):
        sr.fix_block(parts, "annotations", 8, token="rail-block")
        sr.find_node(parts["layout"], "annotations")["place"]["block"] = "start"
    plain = _render(tmp_path, name="plain", configure=short)
    rendered = _render(tmp_path, heading={"text": "Notes"}, name="short", configure=short)
    assert HEADING not in _by_id(rendered)
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:annotations:too-small" in rendered.surface.diagnostics
    assert rendered.artifact.content == plain.artifact.content  # nothing was reserved: the surface is as without


def test_an_absent_rail_has_no_heading_and_changes_nothing(tmp_path):
    plain = _render(tmp_path, name="plain", notes=False)
    headed = _render(tmp_path, heading={"text": "Notes", "block": "header-row"}, name="headed", notes=False)
    assert HEADING not in _by_id(headed) and "annotations" not in {slot.slot_id for slot in headed.surface.slots}
    assert headed.artifact.content == plain.artifact.content


def test_absent_declarations_are_byte_identical_whether_or_not_the_theme_declares_the_role(tmp_path):
    bare = _render(tmp_path, name="a", role=False)
    with_role = _render(tmp_path, name="b", role=True)
    assert HEADING not in _by_id(with_role)
    assert [item.scene_id for item in bare.surface.primitives] == [item.scene_id for item in with_role.surface.primitives]
    assert [item.bounds for item in bare.surface.primitives] == [item.bounds for item in with_role.surface.primitives]
    assert with_role.artifact.content == bare.artifact.content


def test_a_theme_without_the_role_draws_the_copy_in_the_body_text_role(tmp_path):
    rendered = _render(tmp_path, heading={"text": "Notes"}, role=False)
    heading = _by_id(rendered)[HEADING]
    assert heading.text == "Notes" and heading.visual_role == "text" and heading.purpose == "slot-heading"


def _findings(rendered):
    return [item for item in evaluate_scene_contrast(scene_document(rendered.scene)) if item.primitive_id == HEADING]


def test_the_heading_is_ground_text_and_a_faint_one_fails_the_contrast_gate(tmp_path):
    muted = _render(tmp_path, heading={"text": "Notes"}, name="muted")
    assert [item for item in _findings(muted) if item.severity == "error"] == []  # B4: a muted ink passes
    faint = _render(tmp_path, heading={"text": "Notes"}, name="faint", colour="surfaceRaised")
    errors = [item for item in _findings(faint) if item.severity == "error"]
    assert errors, "the gate must judge the heading as ground text"


def test_a_legend_slot_takes_a_heading_and_its_entries_start_below_it(tmp_path):
    def legend(parts):
        sr.find_node(parts["layout"], "legend")["heading"] = {"text": "Key"}
    plain = _render(tmp_path, name="plain", notes=False, detail=DETAIL)
    headed = _render(tmp_path, name="headed", notes=False, configure=legend, detail=DETAIL)
    heading = _by_id(headed)["slot-heading:legend"]
    slot = _slot(headed, "legend")
    assert _inside(heading.bounds, slot.bounds)
    entries = [item for item in headed.surface.primitives if item.slot_id == "legend" and item.scene_id != "slot-heading:legend"]
    assert entries and all(item.bounds[1] >= _bottom(heading.bounds) - 0.01 for item in entries)
    assert slot.bounds[3] > _slot(plain, "legend").bounds[3]  # the slot completes taller by the caption


def test_a_slot_whose_source_has_no_content_draws_no_caption(tmp_path):
    def legend(parts):
        sr.find_node(parts["layout"], "legend")["heading"] = {"text": "Key"}
    rendered = _render(tmp_path, notes=False, configure=legend)  # no review detail: an empty legend
    assert "slot-heading:legend" not in _by_id(rendered)
    assert "I_LAYOUT_SLOT_HEADING_OMITTED:legend:no-content" in rendered.surface.diagnostics


ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}


def test_a_notes_slot_takes_a_heading_and_its_lines_start_below_it(tmp_path):
    def notes(parts):
        sr.find_node(parts["layout"], "notes")["heading"] = {"text": "Remarks"}

    def render(name, configure):
        directory = tmp_path / name
        directory.mkdir()
        parts = sr.bundle()
        _with_heading_role(parts)
        configure(parts)
        source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30)})
        source["annotations"] = {"n1": {"kind": "note", "text": "A project note.", "anchor": {"object": "a"}}}
        return sr.render(directory, source, presentation=parts)

    plain, headed = render("plain", lambda parts: None), render("headed", notes)
    heading, line = _by_id(headed)["slot-heading:notes"], _by_id(headed)["note:n1"]
    assert heading.text == "REMARKS" and _inside(heading.bounds, _slot(headed, "notes").bounds)
    assert line.bounds[1] >= _bottom(heading.bounds) - 0.01
    assert _slot(headed, "notes").bounds[3] > _slot(plain, "notes").bounds[3]  # the slot is taller by the caption


def test_a_summary_slot_takes_a_heading_and_its_runs_start_below_it(tmp_path):
    slot = {"id": "summary", "kind": "slot", "source": "summary", "inlineSize": "content", "blockSize": "content",
            "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": "preferred",
            "overflow": "ellipsize-with-source"}
    profile = {"version": "chrona/summary-profile/v0.1", "kind": "summary-profile", "id": "figures",
               "body": {"panels": [{"id": "key", "title": "Key figures", "presentation": "figures", "metrics": [
                   {"id": "countdown", "source": {"figure": "countdown"}, "label": "DAYS", "format": "count"}]}]}}

    def render(name, heading):
        directory = tmp_path / name
        directory.mkdir()
        parts = sr.bundle("control-room-dark")
        parts["view"]["body"]["figures"] = [{"id": "countdown", "kind": "daysUntil",
                                             "to": {"period": "window", "side": "start"}}]
        node = deepcopy(slot)
        if heading:
            node["heading"] = {"text": "Figures"}
            _with_heading_role(parts)
        parts["layout"]["root"]["children"].insert(1, node)
        source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40), "launch": sr.point("launch", date(2026, 3, 20), owner="b")})
        source["periods"] = {"window": {"title": "Window", "start": {"object": "launch", "endpoint": "at"}, "end": "2026-03-30"}}
        return sr.render(directory, source, presentation=parts, actual=ACTUAL, summary=profile)

    plain, headed = render("plain", False), render("headed", True)
    heading = _by_id(headed)["slot-heading:summary"]
    runs = [item for item in headed.surface.primitives if item.scene_id.startswith("summary:")]
    assert runs and all(item.bounds[1] >= _bottom(heading.bounds) - 0.01 for item in runs)
    assert _inside(heading.bounds, _slot(headed, "summary").bounds)
    first = lambda rendered: min(item.bounds[1] for item in rendered.surface.primitives if item.scene_id.startswith("summary:"))  # noqa: E731
    assert first(headed) > first(plain)


def test_a_tall_caption_pushes_the_rail_content_below_it_not_merely_where_it_already_was(tmp_path):
    def tall(parts):
        parts["theme"]["body"]["values"]["slot-heading-size"] = {"type": "number", "value": 90}
    plain = _render(tmp_path, name="plain")
    rendered = _render(tmp_path, heading={"text": "Notes", "block": "top"}, name="tall", configure=tall)
    heading = _by_id(rendered)[HEADING]
    content = _rail_content(rendered)
    assert content and all(item.bounds[1] >= _bottom(heading.bounds) - 0.01 for item in content)
    assert min(item.bounds[1] for item in content) > min(item.bounds[1] for item in _rail_content(plain)) + 50


def test_every_adapter_draws_the_caption_as_ordinary_text(tmp_path):
    """Typst and TikZ draw only Scenes without markers, symbols and patterns: a spans-only slide with a legend caption."""
    parts = sr.bundle("executive-light")
    _with_heading_role(parts)
    sr.find_node(parts["layout"], "legend")["heading"] = {"text": "Key", "align": "start"}
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30), "b": sr.span("b", date(2026, 3, 9), 20)})
    (tmp_path / "r").mkdir()
    rendered = sr.render(tmp_path / "r", source, presentation=parts, detail=DETAIL)
    surface = rendered.scene.surfaces[0]
    typst, tikz = render_v05_typst(surface), render_v05_tikz(surface)
    assert ("// scene-id: slot-heading:legend source-ref: legend" in typst
            and "% scene-id: slot-heading:legend source-ref: legend" in tikz)
    assert 'weight: 700, size: 11pt, tracking: 1.1pt' in typst and "[KEY]]" in typst  # completed size, tracking, text
    assert r"\fontsize{11pt}{15.4pt}" in tikz and r"\textls[100]{KEY}" in tikz
    assert 'fill: rgb("#4B5563")' in typst and "text=#4B5563" in tikz  # the muted ink the Theme role binds
    assert ">KEY<" in rendered.artifact.content.decode()
    path = tmp_path / "board.svg"
    path.write_bytes(rendered.artifact.content)
    image = Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_path=str(path), zoom=1)))).convert("RGB")
    heading = next(item for item in rendered.surface.primitives if item.scene_id == "slot-heading:legend")
    left, top, width, height = (round(value) for value in heading.bounds)
    crop = image.crop((left, top, left + max(1, width), top + max(1, height)))
    assert min(crop.getdata()) != max(crop.getdata())  # PNG (resvg of this SVG) shows ink where the caption is


def test_a_caption_goes_with_a_slot_the_completed_footer_band_carried_down(tmp_path):
    """The default Layout puts `annotations` under the footer; panels that complete taller push it down."""
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "footer-detail", "body": {
        "legend": [{"role": "planned", "label": "Planned"}],
        "groupDetails": [{"groupId": f"team-{index}", "label": f"Team {index}",
                          "description": "A long description that wraps over several lines of the footer. " * 3}
                         for index in range(3)]}}

    directory = tmp_path / "headed"
    directory.mkdir()
    parts = sr.bundle()
    _with_heading_role(parts)
    _filled_notes(parts)
    sr.fix_inline(parts, "annotations", 300, token="rail-width")
    sr.find_node(parts["layout"], "annotations")["heading"] = {"text": "Notes"}
    source = sr.chain_project()
    sr.add_notes(source, parts["view"], TARGETS, [_rail_candidate()], words=3)
    headed = sr.render(directory, source, presentation=parts, detail=detail)
    heading, slot = _by_id(headed)[HEADING], _slot(headed, "annotations")
    assert slot.bounds[1] > _slot(headed, "group-details").bounds[1]  # the successor stands under the footer
    assert heading.bounds[1] == pytest.approx(slot.bounds[1]) and _inside(heading.bounds, slot.bounds)
