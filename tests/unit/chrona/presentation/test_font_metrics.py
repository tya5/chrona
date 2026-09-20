from copy import deepcopy
import pytest

from chrona.presentation.font_metrics import resolve_font_metrics
from chrona.presentation.presentation_settings import PresentationSettingsError, resolve_presentation_settings


def test_font_metrics_measurement_is_asset_bound_and_deterministic():
    settings = resolve_presentation_settings.__globals__["builtin_bases"]()["executive-v0.2"]
    probe = deepcopy(settings)
    descriptor = probe["context"]["fontMetrics"]
    descriptor["assets"][0]["contentIdentity"] = "sha256:" + "1" * 64
    with pytest.raises(PresentationSettingsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics(probe["theme"]["fontFamily"], descriptor)
    metrics = resolve_font_metrics(settings["theme"]["fontFamily"], settings["context"]["fontMetrics"])
    assert metrics.width("Chrona", 20) == metrics.width("Chrona", 20)
    assert metrics.width("Chrona", 20) > 0
    assert metrics.path.name == "nimbus-sans-regular-v1.json"


def test_font_metrics_rejects_a_different_declared_weight():
    settings = resolve_presentation_settings.__globals__["builtin_bases"]()["executive-v0.2"]
    descriptor = deepcopy(settings["context"]["fontMetrics"])
    descriptor["assets"][1]["path"] = descriptor["assets"][0]["path"]
    descriptor["assets"][1]["contentIdentity"] = descriptor["assets"][0]["contentIdentity"]
    with pytest.raises(PresentationSettingsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics(settings["theme"]["fontFamily"], descriptor, weight=700)


def test_font_metrics_rejects_path_traversal():
    settings = resolve_presentation_settings.__globals__["builtin_bases"]()["executive-v0.2"]
    descriptor = deepcopy(settings["context"]["fontMetrics"])
    descriptor["assets"][0]["path"] = "../outside.json"
    with pytest.raises(PresentationSettingsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics(settings["theme"]["fontFamily"], descriptor)
