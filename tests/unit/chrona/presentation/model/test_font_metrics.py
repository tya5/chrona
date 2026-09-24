from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
import pytest

from chrona.presentation.model.font_metrics import resolve_font_metrics
from chrona.presentation.model.font_metrics import FontMetricsError


def descriptor():
    assets = []
    for weight, name, face in ((400, "noto-sans-cjk-jp-regular-v1.json", "regular"), (700, "noto-sans-cjk-jp-bold-v1.json", "bold")):
        payload = files("chrona.resources").joinpath("font_metrics", name).read_bytes()
        font = files("chrona.resources").joinpath("fonts", f"noto-sans-cjk-jp-{face}-v1.ttf")
        assets.append({"family": "Noto Sans CJK JP", "weight": weight,
                       "metrics": {"path": f"font_metrics/{name}", "contentIdentity": "sha256:" + sha256(payload).hexdigest()},
                       "font": {"path": f"fonts/noto-sans-cjk-jp-{face}-v1.ttf", "contentIdentity": "sha256:" + sha256(font.read_bytes()).hexdigest()}})
    return {"algorithm": "declared-metrics-v2", "assets": assets, "missingFont": "diagnose"}


def test_font_metrics_measurement_is_asset_bound_and_deterministic():
    value = descriptor(); probe = deepcopy(value)
    probe["assets"][0]["metrics"]["contentIdentity"] = "sha256:" + "1" * 64
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans CJK JP", probe)
    metrics = resolve_font_metrics("Noto Sans CJK JP", value)
    assert metrics.width("Chrona", 20) == metrics.width("Chrona", 20)
    assert metrics.width("Chrona", 20) > 0
    assert metrics.cap_height_at(20) == 14.66
    assert metrics.metrics_path.name == "noto-sans-cjk-jp-regular-v1.json"
    assert metrics.width("日本語", 20) > metrics.width("abc", 20)


def test_font_metrics_rejects_a_different_declared_weight():
    value = descriptor()
    value["assets"][1]["metrics"] = value["assets"][0]["metrics"]
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans CJK JP", value, weight=700)


def test_font_metrics_rejects_path_traversal():
    value = descriptor(); value["assets"][0]["metrics"]["path"] = "../outside.json"
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Noto Sans CJK JP", value)


def test_font_metrics_rejects_an_unmeasured_glyph_instead_of_using_notdef_width():
    metrics = resolve_font_metrics("Noto Sans CJK JP", descriptor())
    with pytest.raises(FontMetricsError, match="E_FONT_GLYPH_UNAVAILABLE") as error:
        metrics.width("\U0010ffff", 12)
    assert "U+10FFFF" in error.value.detail
