from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
import pytest

from chrona.presentation.model.font_metrics import resolve_font_metrics
from chrona.presentation.model.font_metrics import FontMetricsError


def descriptor():
    assets = []
    for weight, name in ((400, "nimbus-sans-regular-v1.json"), (700, "nimbus-sans-bold-v1.json")):
        payload = files("chrona.resources").joinpath("font_metrics", name).read_bytes()
        assets.append({"family": "Nimbus Sans", "weight": weight, "path": f"font_metrics/{name}", "contentIdentity": "sha256:" + sha256(payload).hexdigest()})
    return {"assets": assets, "missingFont": "diagnose"}


def test_font_metrics_measurement_is_asset_bound_and_deterministic():
    value = descriptor(); probe = deepcopy(value)
    probe["assets"][0]["contentIdentity"] = "sha256:" + "1" * 64
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Nimbus Sans", probe)
    metrics = resolve_font_metrics("Nimbus Sans", value)
    assert metrics.width("Chrona", 20) == metrics.width("Chrona", 20)
    assert metrics.width("Chrona", 20) > 0
    assert metrics.cap_height_at(20) == 14.58
    assert metrics.path.name == "nimbus-sans-regular-v1.json"


def test_font_metrics_rejects_a_different_declared_weight():
    value = descriptor()
    value["assets"][1]["path"] = value["assets"][0]["path"]
    value["assets"][1]["contentIdentity"] = value["assets"][0]["contentIdentity"]
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Nimbus Sans", value, weight=700)


def test_font_metrics_rejects_path_traversal():
    value = descriptor(); value["assets"][0]["path"] = "../outside.json"
    with pytest.raises(FontMetricsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics("Nimbus Sans", value)
