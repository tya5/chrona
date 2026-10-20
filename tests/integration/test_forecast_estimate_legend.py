"""An estimated delta retains its explanation when forecast ink is encoded away."""
from copy import deepcopy
from xml.etree import ElementTree

import yaml

from chrona.usecases.draft_render import render_draft
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from tests.integration.test_forecast_occurrence_coverage import _request
from tests.support import synthetic_review as sr


def _encoded_request(tmp_path, *, placement="plot", folded=False):
    request = _request(tmp_path, placement=placement, folded=folded)
    view = yaml.safe_load(request.view.read_text(encoding="utf-8"))
    body = view["body"]
    body["colorEncoding"] = {
        "scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["team"]}
    if placement == "plot":
        # Keep the channel visible on plot labels only; table cells remain title-only.
        body["tableColumns"] = [column for column in body["tableColumns"] if column["id"] != "Delta"]
    sr._write(request.view, view)

    parts = sr.bundle("technical-print")
    theme = deepcopy(parts["theme"])
    theme["body"].setdefault("colorScales", {})["owner"] = {"slots": {"team": "owner-ink"}}
    scheme = deepcopy(parts["scheme"])
    scheme["body"]["categories"]["owner-ink"] = "#3456A0"
    theme_path = sr._write(tmp_path / "theme.yaml", theme)
    scheme_path = sr._write(tmp_path / "scheme.yaml", scheme)
    return request, theme_path, scheme_path


def _render(request, theme, scheme):
    # The draft request uses the same pinned bundle as its base; a project-specific
    # scheme override supplies the one encoding color for this synthetic control.
    from dataclasses import replace
    return render_draft(replace(request, forecast=True, theme=theme, scheme=scheme)).rendered


def test_encoded_forecast_delta_keeps_text_only_estimate_explanation(tmp_path):
    request, theme, scheme = _encoded_request(tmp_path, placement="plot")
    rendered = _render(request, theme, scheme)
    validate_scene_document(scene_document(rendered.scene))
    primitives = rendered.surface.primitives
    delta = next(item for item in primitives if item.purpose == "forecast-finish-delta")
    label = next(item for item in primitives
                 if item.purpose == "legend-label" and item.text == "Forecast (* estimated)")

    assert delta.text.endswith("*")
    assert not any(item.scene_id == "legend-swatch:forecast" for item in primitives)
    assert label.source_ref == "forecast"
    svg_text = "".join(ElementTree.fromstring(rendered.artifact.content).itertext())
    assert "Forecast (* estimated)" in svg_text


def test_encoded_forecast_key_is_omitted_without_visible_estimate_text(tmp_path):
    request, theme, scheme = _encoded_request(tmp_path, placement="plot")
    # A new forecast item has a delta-channel value (`new`) but no estimated
    # delta; this keeps the forecast capability present without an asterisk.
    snapshot = yaml.safe_load(request.snapshot.read_text(encoding="utf-8"))
    snapshot["objects"].clear()
    sr._write(request.snapshot, snapshot)
    rendered = _render(request, theme, scheme)
    validate_scene_document(scene_document(rendered.scene))

    assert not any(item.text.endswith("*") for item in rendered.surface.primitives if item.kind == "Text")
    assert not any(item.purpose == "legend-label" and item.text == "Forecast (* estimated)"
                   for item in rendered.surface.primitives)
    assert not any(item.scene_id == "legend-swatch:forecast" for item in rendered.surface.primitives)


def test_unencoded_incomplete_forecast_keeps_its_ordinary_swatch(tmp_path):
    rendered = _render(_request(tmp_path, placement="plot"), theme=None, scheme=None)

    assert any(item.scene_id == "legend-swatch:forecast" for item in rendered.surface.primitives)
    assert any(item.purpose == "legend-label" and item.text == "Forecast (* estimated)"
               for item in rendered.surface.primitives)
    assert any(item.purpose == "forecast-finish-delta" and item.text.endswith("*")
               for item in rendered.surface.primitives)


def test_encoded_table_only_estimate_keeps_explanation_without_plot_swatch(tmp_path):
    request, theme, scheme = _encoded_request(tmp_path, placement="table")
    rendered = _render(request, theme, scheme)

    assert any(item.kind == "Text" and item.purpose == "table-cell" and item.text.endswith("*")
               for item in rendered.surface.primitives)
    assert not any(item.purpose == "forecast-finish-delta" for item in rendered.surface.primitives)
    assert not any(item.scene_id == "legend-swatch:forecast" for item in rendered.surface.primitives)
    assert any(item.purpose == "legend-label" and item.text == "Forecast (* estimated)"
               for item in rendered.surface.primitives)


def test_mixed_encoded_span_and_unencoded_folded_point_keep_real_swatch(tmp_path):
    request, theme, scheme = _encoded_request(tmp_path, placement="plot", folded=True)
    rendered = _render(request, theme, scheme)

    assert any(item.scene_id == "variance:group-header:team:gate" and item.text.endswith("*")
               for item in rendered.surface.primitives)
    # The folded point is still drawn with the ordinary forecast stroke while the
    # span fill is encoded; the semantic forecast key therefore remains truthful.
    assert any(item.scene_id == "planned:a:a" and item.paint.fill == "#3456A0"
               for item in rendered.surface.primitives)
    assert any(item.scene_id == "planned:group-header:team:gate:part0"
               and item.paint.fill is None and item.paint.stroke is not None
               for item in rendered.surface.primitives)
    assert any(item.scene_id == "legend-swatch:forecast" for item in rendered.surface.primitives)
    assert any(item.purpose == "legend-label" and item.text == "Forecast (* estimated)"
               for item in rendered.surface.primitives)


def test_encoded_completed_forecast_has_no_estimate_explanation_witness(tmp_path):
    request, theme, scheme = _encoded_request(tmp_path, placement="plot")
    actual = yaml.safe_load(request.actual.read_text(encoding="utf-8"))
    actual["body"]["asOf"] = "2026-03-09"
    for observation in actual["body"]["observations"]:
        observation["actual"]["finish"] = "2026-01-12" if observation["projectObjectId"] == "a" else "2026-03-09"
    request_actual = sr._write(tmp_path / "completed-actual.yaml", actual)
    from dataclasses import replace
    request = replace(request, actual=request_actual)
    rendered = _render(request, theme, scheme)

    assert not any(item.kind == "Text" and item.purpose == "forecast-finish-delta"
                   and item.text.endswith("*") for item in rendered.surface.primitives)
    assert not any(item.scene_id == "legend-swatch:forecast" for item in rendered.surface.primitives)
    assert not any(item.purpose == "legend-label" and item.text == "Forecast (* estimated)"
                   for item in rendered.surface.primitives)
