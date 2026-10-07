"""#1096: `viewerFit: text-follows-box` on chips, legend items, table cells, bar labels, titles and vertical group tags.

Synthetic Projects through the packaged `executive-light` bundle; no `examples/` input. The rule is checked on the
emitted SVG against the published Scene, as in #1050: every pinned line carries the width Layout finally measured,
geometry is unchanged, the default is byte-identical, and a declaration the family cannot honour fails at its pointer.
"""
from __future__ import annotations

import re
from datetime import date

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.perceptibility import evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail", "body": {"legend": [
    {"role": "planned", "label": "Planned"}, {"role": "actual", "label": "Actual"}]}}
FIT = "text-follows-box"


def _column(column_id, source, **extra):
    return {"id": column_id, "source": source, "missing": "em-dash", "align": "start", "width": "content",
            "headerOrientation": "horizontal", **extra}


def _parts(*, roles=None, chips=False, secondary=False, vertical=False):
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    columns = [_column("Work package", "title"), _column("Phase", {"field": "phase"})]
    if secondary:
        measure = {key: value for key, value in body["roles"]["text"].items() if key not in {"iconScale", "iconGap"}}
        body["roles"]["table-cell-secondary"] = dict(measure)
        columns[1]["textRole"] = "table-cell-secondary"
    parts["view"]["body"]["tableColumns"] = columns
    if chips:
        body["values"]["chip-padding"] = {"type": "number", "value": 0.1}
        body["roles"]["member-label-chip"] = {"backgroundTreatment": "fill", "chipPadding": "chip-padding"}
        body["colorBindings"]["member-label-chip.fill"] = "surfaceRaised"
    if vertical:
        tt.with_vertical_groups(parts)
    for role, declaration in (roles or {}).items():
        body["roles"].setdefault(role, {}).update(declaration)
    return parts


def _render(tmp_path, name="r", **kwargs):
    directory = tmp_path / name
    directory.mkdir()
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"),
                         "b": sr.span("b", date(2026, 3, 9), 20, title="Beta Release Candidate")})
    for key, phase in (("a", "Build"), ("b", "Verify")):
        source["objects"][key]["fields"] = {**source["objects"][key].get("fields", {}), "phase": phase}
    parts = _parts(**kwargs)
    return sr.render(directory, source, presentation=parts, detail=DETAIL)


def _svg(rendered):
    return rendered.artifact.content.decode("utf-8")


def _element(svg, scene_id):
    match = re.search(rf'<text data-scene-id="{re.escape(scene_id)}"[^>]*>.*?</text>', svg, re.S)
    assert match, scene_id
    return match.group(0)


def _pinned(rendered, selector):
    """The selected Text primitives, each checked against its SVG element; returns them."""
    svg = _svg(rendered)
    found = [item for item in rendered.surface.primitives if item.kind == "Text" and selector(item)]
    assert found
    for item in found:
        fit = item.text_layout.fit
        assert fit is not None and fit.mode == FIT, item.scene_id
        lengths = [float(value) for value in re.findall(r'textLength="([^"]+)"', _element(svg, item.scene_id))]
        scale = item.text_layout.horizontal_scale
        assert lengths == pytest.approx([size / scale for size in fit.line_inline_sizes], abs=0.002), item.scene_id
        assert max(fit.line_inline_sizes) == pytest.approx(item.bounds[2] if item.text_layout.rotation_degrees == 0
                                                           else item.bounds[3], abs=0.01), item.scene_id
    return found


def _unpinned(rendered, selector):
    found = [item for item in rendered.surface.primitives if item.kind == "Text" and selector(item)]
    assert found
    assert all(item.text_layout.fit is None for item in found)
    return found


def test_the_default_and_an_explicit_raw_are_byte_identical_for_every_family(tmp_path):
    plain = _render(tmp_path, "a", chips=True, vertical=True)
    raw = _render(tmp_path, "b", chips=True, vertical=True,
                  roles={role: {"viewerFit": "raw"} for role in ("text", "legend", "heading", "groupHeader",
                                                                 "member-label-chip", "numeric")})
    assert raw.artifact.content == plain.artifact.content
    assert scene_document(plain.scene)["version"] == "chrona/scene/v0.6"
    assert b"textLength" not in plain.artifact.content


def test_a_table_cell_is_pinned_through_its_text_role_and_the_other_column_is_not(tmp_path):
    rendered = _render(tmp_path, secondary=True, roles={"table-cell-secondary": {"viewerFit": FIT}})
    _pinned(rendered, lambda item: item.purpose == "table-cell" and item.table_column_id == "Phase")
    _unpinned(rendered, lambda item: item.purpose == "table-cell" and item.table_column_id == "Work package")


def test_the_shared_text_role_pins_cells_and_bar_labels_alike(tmp_path):
    rendered = _render(tmp_path, roles={"text": {"viewerFit": FIT}})
    _pinned(rendered, lambda item: item.purpose == "table-cell")
    _pinned(rendered, lambda item: item.purpose == "member-label")


def test_legend_items_are_pinned_with_the_declared_adjust(tmp_path):
    rendered = _render(tmp_path, roles={"legend": {"viewerFit": FIT, "viewerFitAdjust": "spacingAndGlyphs"}})
    found = _pinned(rendered, lambda item: item.purpose == "legend-label")
    assert len(found) == 2 and {item.text_layout.fit.adjust for item in found} == {"spacingAndGlyphs"}
    assert 'lengthAdjust="spacingAndGlyphs"' in _element(_svg(rendered), found[0].scene_id)
    _unpinned(rendered, lambda item: item.purpose == "table-cell")


def test_the_title_plate_is_pinned_through_the_heading_role(tmp_path):
    rendered = _render(tmp_path, roles={"heading": {"viewerFit": FIT}})
    _pinned(rendered, lambda item: item.purpose == "title-text")
    _unpinned(rendered, lambda item: item.purpose == "legend-label")


def test_a_chip_role_pins_the_label_that_carries_the_chip_and_nothing_else(tmp_path):
    rendered = _render(tmp_path, chips=True, roles={"member-label-chip": {"viewerFit": FIT}})
    chips = [item for item in rendered.surface.primitives if item.visual_role == "member-label-chip"]
    assert chips
    pinned = _pinned(rendered, lambda item: item.purpose == "member-label" and f"chip:{item.scene_id}" in {c.scene_id for c in chips})
    assert len(pinned) == len(chips)
    _unpinned(rendered, lambda item: item.purpose == "table-cell")
    # the chip box keeps its measured geometry: it is the label plus its padding in every mode
    raw = _render(tmp_path, "raw", chips=True)
    assert [(item.scene_id, item.bounds) for item in rendered.surface.primitives] == [
        (item.scene_id, item.bounds) for item in raw.surface.primitives]


def test_a_chip_role_without_a_chip_does_not_pin_the_label(tmp_path):
    parts_roles = {"member-label-chip": {"viewerFit": FIT}}
    rendered = _render(tmp_path, chips=False, roles=parts_roles)  # the chip role has no fill: no chip is drawn
    _unpinned(rendered, lambda item: item.purpose == "member-label")


def test_a_vertical_group_tag_is_pinned_in_its_rotated_frame(tmp_path):
    rendered = _render(tmp_path, vertical=True, roles={"groupHeader": {"viewerFit": FIT}})
    found = _pinned(rendered, lambda item: item.purpose == "group-header")
    assert any(item.text_layout.rotation_degrees == 90 for item in found)  # a sideways run is turned a quarter
    for item in found:
        element = _element(_svg(rendered), item.scene_id)
        assert ("rotate(90 " in element) == (item.text_layout.rotation_degrees == 90)


def test_pinning_changes_no_geometry_paint_or_finding(tmp_path):
    roles = {role: {"viewerFit": FIT} for role in ("text", "legend", "heading", "numeric")}
    raw = _render(tmp_path, "raw")
    fitted = _render(tmp_path, "fit", roles=roles)
    assert [(item.scene_id, item.bounds, item.paint) for item in fitted.surface.primitives] == [
        (item.scene_id, item.bounds, item.paint) for item in raw.surface.primitives]
    assert evaluate_scene_contrast(scene_document(fitted.scene)) == evaluate_scene_contrast(scene_document(raw.scene))
    assert (evaluate_scene_perceptibility(scene_document(fitted.scene))
            == evaluate_scene_perceptibility(scene_document(raw.scene)))
    assert scene_document(fitted.scene)["version"] == "chrona/scene/v0.7"
    serialize_scene(fitted.scene)
    assert _render(tmp_path, "again", roles=roles).artifact.content == fitted.artifact.content


@pytest.mark.parametrize("role,kwargs", [("legend", {}), ("text", {}), ("heading", {}), ("groupHeader", {})])
def test_a_box_that_follows_its_text_is_refused_where_there_is_no_box_to_follow(tmp_path, role, kwargs):
    with pytest.raises((RenderFailed, ClosureError)) as raised:
        _render(tmp_path, roles={role: {"viewerFit": "box-follows-text"}}, **kwargs)
    error = raised.value
    assert (getattr(error, "code", None) or error.diagnostic_id) == "E_THEME_TOKEN_TYPE"
    assert error.source_ref == f"/body/roles/{role}/viewerFit"


def test_a_role_with_no_text_to_fit_still_cannot_declare_the_property(tmp_path):
    with pytest.raises(Exception) as raised:
        _render(tmp_path, roles={"planned": {"viewerFit": FIT}})
    assert "E_THEME_ROLE_PROPERTY_UNSUPPORTED" in repr(raised.value) + str(raised.value) + repr(
        getattr(raised.value, "diagnostic_id", ""))
