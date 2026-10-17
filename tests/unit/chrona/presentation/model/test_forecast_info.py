"""Forecast findings cross the presentation boundary without wrapping fatal outcomes."""
import json

import pytest

from chrona.core.diagnostics import Diagnostic
from chrona.presentation.model.info_diagnostics import ForecastInfo, PresentationInfo


@pytest.mark.parametrize("code", (
    "I_FORECAST_MOVED",
    "I_FORECAST_START_UNOBSERVED",
    "I_FORECAST_ROLLUP_OBSERVATION_CONFLICT",
    "E_FIXED_TARGET_VIOLATION",
))
def test_forecast_info_preserves_published_code_and_scene_payload(code):
    details = {"count": 0} if code == "I_FORECAST_MOVED" else {"target": "2026-10-17"}
    info = ForecastInfo(Diagnostic(code, "Forecast finding", "/objects/task-a", details=details))

    assert isinstance(info, PresentationInfo)
    assert info.code == code
    assert info.payload() == {
        "message": "Forecast finding", "path": "/objects/task-a", "details": details,
    }
    encoded_code, encoded_payload = info.scene_diagnostic().split(":", 1)
    assert encoded_code == code
    assert json.loads(encoded_payload) == info.payload()
    assert info.scene_diagnostic() == code + ":" + json.dumps(
        info.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def test_forecast_info_omits_absent_optional_fields():
    info = ForecastInfo(Diagnostic("I_FORECAST_START_UNOBSERVED", "No start observation"))
    assert info.payload() == {"message": "No start observation"}


@pytest.mark.parametrize("diagnostic", (
    Diagnostic("E_SCHEDULING_FAILED", "Fatal schedule failure"),
    Diagnostic("I_FORECAST_UNKNOWN", "Unpublished forecast finding"),
    object(),
))
def test_forecast_info_rejects_unpublished_codes_and_non_diagnostics(diagnostic):
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID"):
        ForecastInfo(diagnostic)
