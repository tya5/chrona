"""Transformed group headers keep their completed width equal to the painted run (#1336)."""
from __future__ import annotations

from importlib.resources import files

import pytest

from chrona.presentation.layout.text import ScaledMetric, measure_text_width
from chrona.presentation.model.font_metrics import resolve_font_metrics_catalog
from chrona.resources import safe_load
from tests.integration.test_group_header_text_extent import _assert_svg_bounds, _by_id, _parts, _render, _source


def _transformed_parts(*, marked: bool, transform: str, tab: float | None = None):
    parts = _parts(marked=False, extent="text", tab=(tab, "start") if tab is not None else None)
    body = parts["theme"]["body"]
    body["values"].update({
        "measure-transform": {"type": "textTransform", "value": transform},
        "measure-scale": {"type": "number", "value": 0.92},
        "measure-spacing": {"type": "number", "value": 0.5},
    })
    body["roles"]["groupHeader"].update({
        "textTransform": "measure-transform",
        "horizontalScale": "measure-scale",
        "letterSpacing": "measure-spacing",
    })
    if marked:
        body["roles"]["header-emphasis"] = {
            key: value for key, value in body["roles"]["groupHeader"].items()
            if key in {"fontFamily", "fontWeight", "fontSize", "lineHeight", "letterSpacing", "textTransform",
                       "numericSpacing", "horizontalScale"}
        }
        body["colorBindings"]["header-emphasis.fill"] = "warning"
        parts["view"]["body"]["grouping"]["header"] = {"text": "{title|header-emphasis}"}
    return parts


def _source_with_title(title: str):
    source = _source()
    source["entities"]["team-0"]["title"] = title
    return source


@pytest.mark.parametrize("marked", [False, True], ids=["plain", "role-marked"])
def test_uppercase_compressed_header_width_matches_the_same_painted_text(tmp_path, marked):
    # Lowercase i has a substantially narrower advance than uppercase I in the bundled face. Comparing a transformed
    # source with an untransformed source already in its painted case checks the native measured width independently.
    source = _source_with_title("iiiiiiii")
    painted_source = _source_with_title("IIIIIIII")
    transformed = _render(tmp_path, _transformed_parts(marked=marked, transform="uppercase"),
                          source=source, name="transformed")
    reference = _render(tmp_path, _transformed_parts(marked=marked, transform="none"),
                        source=painted_source, name="painted-reference")

    scene_id = "group-header:team-0#run0" if marked else "group-header:team-0"
    header, painted = _by_id(transformed)[scene_id], _by_id(reference)[scene_id]
    assert header.text == "IIIIIIII"
    assert header.bounds[2] == pytest.approx(painted.bounds[2], abs=1e-6)

    band_id = "group-header-band:team-0"
    band = _by_id(transformed)[band_id]
    assert band.bounds[0] + band.bounds[2] == pytest.approx(header.bounds[0] + header.bounds[2], abs=1e-6)
    _assert_svg_bounds(transformed, band_id)


def test_role_marked_ellipsis_uses_transformed_width_and_band_end(tmp_path):
    source = _source_with_title("i" * 200)
    transformed = _render(tmp_path, _transformed_parts(marked=True, transform="uppercase", tab=600),
                          source=source, name="transformed-ellipsis")
    scene_id = "group-header:team-0#run0"
    header = _by_id(transformed)[scene_id]
    assert header.text.endswith("…")
    assert header.text == header.text.upper()

    # Re-render the exact visible source without a transform: its measured width must be identical to the transformed
    # run, even after the bounded ellipsis decision.
    reference_source = _source_with_title(header.text)
    reference = _render(tmp_path, _transformed_parts(marked=True, transform="none", tab=600),
                        source=reference_source, name="plain-ellipsis-reference")
    assert _by_id(reference)[scene_id].bounds[2] == pytest.approx(header.bounds[2], abs=1e-6)
    band_id = "group-header-band:team-0"
    band = _by_id(transformed)[band_id]
    table = next(slot.bounds for slot in transformed.surface.slots if slot.slot_id == "table")
    expected_right = min(table[0] + table[2], header.bounds[0] + header.bounds[2])
    assert band.bounds[0] + band.bounds[2] == pytest.approx(expected_right, abs=1e-6)
    _assert_svg_bounds(transformed, band_id)


def test_transform_none_width_includes_declared_spacing_and_compression(tmp_path):
    source = _source_with_title("IIIIIIII")
    parts = _transformed_parts(marked=False, transform="none")
    rendered = _render(tmp_path, parts,
                        source=source, name="untransformed")
    text = _by_id(rendered)["group-header:team-0"]
    assert text.text == "IIIIIIII"
    metrics = resolve_font_metrics_catalog(safe_load(
        files("chrona.resources").joinpath("fonts/default-font-metrics.yaml").read_bytes()))
    layout = text.text_layout
    metric = metrics.select(layout.family, layout.weight)
    expected = measure_text_width("IIIIIIII", font_size=layout.font_size,
                                  font_metrics=ScaledMetric(metric, layout.horizontal_scale),
                                  letter_spacing=layout.letter_spacing, text_transform="none",
                                  numeric_spacing=layout.numeric_spacing)
    assert text.bounds[2] == pytest.approx(expected, abs=1e-6)

    table = next(slot.bounds for slot in rendered.surface.slots if slot.slot_id == "table")
    band = _by_id(rendered)["group-header-band:team-0"]
    assert band.bounds[0] + band.bounds[2] == pytest.approx(
        min(table[0] + table[2], text.bounds[0] + text.bounds[2]), abs=1e-6)
    _assert_svg_bounds(rendered, "group-header-band:team-0")
