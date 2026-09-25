from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
import json
import pytest

from chrona.presentation.model.font_metrics import resolve_font_files, resolve_font_metrics, resolve_font_metrics_catalog
from chrona.presentation.model.font_metrics import FontMetricsError
from chrona.resources import safe_load


def descriptor():
    assets = []
    for weight, name, face in ((400, "noto-sans-regular-v2.json", "regular"), (700, "noto-sans-bold-v2.json", "bold")):
        payload = files("chrona.resources").joinpath("font_metrics", name).read_bytes()
        font = files("chrona.resources").joinpath("fonts", f"noto-sans-{face}-v1.ttf")
        assets.append({"family": "Noto Sans", "weight": weight,
                       "metrics": {"locator": {"provider": "package", "identity": "chrona.resources", "address": f"font_metrics/{name}"}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()},
                       "font": {"locator": {"provider": "package", "identity": "chrona.resources", "address": f"fonts/noto-sans-{face}-v1.ttf"}, "contentIdentity": "sha256:" + sha256(font.read_bytes()).hexdigest()}})
    return {"algorithm": "declared-metrics-v3", "assets": assets, "missingFont": "diagnose"}


def test_font_metrics_measurement_is_asset_bound_and_deterministic():
    value = descriptor(); probe = deepcopy(value)
    probe["assets"][0]["metrics"]["contentIdentity"] = "sha256:" + "1" * 64
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans", probe)
    metrics = resolve_font_metrics("Noto Sans", value)
    assert metrics.width("Chrona", 20) == metrics.width("Chrona", 20)
    assert metrics.width("Chrona", 20) > 0
    assert metrics.cap_height_at(20) == 14.28
    assert metrics.metrics_path.name == "noto-sans-regular-v2.json"
    with pytest.raises(FontMetricsError, match="E_FONT_GLYPH_UNAVAILABLE"):
        metrics.width("日本語", 20)


def test_primary_metrics_select_the_declared_proportional_or_tabular_digit_advances():
    metrics = resolve_font_metrics("Noto Sans", descriptor())
    assert metrics.width("111", 20, numeric_spacing="proportional") < metrics.width("111", 20, numeric_spacing="tabular")
    assert metrics.width("111", 20, numeric_spacing="tabular") == metrics.width("999", 20, numeric_spacing="tabular")


@pytest.mark.parametrize("mutate", [
    lambda payload: payload["numericAdvances"]["tabular"].pop("48"),
    lambda payload: payload["numericAdvances"]["tabular"].__setitem__("49", 1),
])
def test_primary_metrics_reject_incomplete_or_nonuniform_tabular_advances(tmp_path, mutate):
    payload = json.loads(files("chrona.resources").joinpath("font_metrics", "noto-sans-regular-v2.json").read_bytes())
    mutate(payload)
    metric_path = tmp_path / "metrics.json"
    metric_path.write_text(json.dumps(payload), encoding="utf-8")
    descriptor = {"algorithm": "declared-metrics-v3", "missingFont": "diagnose", "assets": [{
        "family": "Noto Sans", "weight": 400,
        "metrics": {"locator": {"provider": "context", "address": "metrics.json"},
                    "contentIdentity": "sha256:" + sha256(metric_path.read_bytes()).hexdigest()},
    }]}
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans", descriptor, asset_root=tmp_path)


def test_font_metrics_rejects_a_different_declared_weight():
    value = descriptor()
    value["assets"][1]["metrics"] = value["assets"][0]["metrics"]
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans", value, weight=700)


def test_catalog_selects_exact_declared_family_weight_and_rejects_missing_face():
    catalog = resolve_font_metrics_catalog(descriptor())

    assert catalog.select("Noto Sans, sans-serif", 400).weight == 400
    assert catalog.select("Noto Sans", 700).weight == 700
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        catalog.select("Noto Sans Mono", 400)
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        catalog.select("Noto Sans", 500)


def test_packaged_catalog_selects_the_bundled_monospace_face():
    value = safe_load(files("chrona.resources").joinpath("fonts", "default-font-metrics.yaml").read_bytes())
    catalog = resolve_font_metrics_catalog(value)

    mono = catalog.select("Noto Sans Mono, monospace", 400)
    assert mono.family == "Noto Sans Mono"
    assert mono.content_identity == "sha256:c886cba7994069f6ba1c1a97c49d3aff58a3c131e6b4710237a452bd67a845a4"


def test_font_metrics_rejects_path_traversal():
    value = descriptor(); value["assets"][0]["metrics"]["locator"]["address"] = "../outside.json"
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans", value)


def test_font_metrics_rejects_an_unmeasured_glyph_instead_of_using_notdef_width():
    metrics = resolve_font_metrics("Noto Sans", descriptor())
    with pytest.raises(FontMetricsError, match="E_FONT_GLYPH_UNAVAILABLE") as error:
        metrics.width("\U0010ffff", 12)
    assert "U+10FFFF" in error.value.detail


def test_metrics_resolution_does_not_read_font_bytes_but_raster_resolution_does():
    value = descriptor()
    value["assets"][0]["font"]["locator"]["address"] = "fonts/missing.ttf"
    assert resolve_font_metrics("Noto Sans", value).width("Chrona", 12) > 0
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE") as error:
        resolve_font_files(value, asset_root=None)
    assert error.value.detail == "fonts/missing.ttf"


def test_draft_substitute_measures_packaged_checkmark_and_records_one_warning():
    value = descriptor()
    value["missingFont"] = "substitute"
    metrics = resolve_font_metrics("Noto Sans", value)
    assert metrics.width("General Availability ✅", 12) > 0
    assert metrics.warnings[0].requested_family == "Noto Sans"
    assert metrics.warnings[0].fallback_family == "Noto Color Emoji Check"
    assert metrics.warnings[0].codepoint == 0x2705
