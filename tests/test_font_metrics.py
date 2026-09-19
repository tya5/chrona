from copy import deepcopy
from hashlib import sha256

import pytest

from chrona.font_metrics import resolve_font_metrics
from chrona.presentation_settings import PresentationSettingsError, resolve_presentation_settings


def test_font_metrics_measurement_is_asset_bound_and_deterministic():
    settings = resolve_presentation_settings.__globals__["builtin_bases"]()["executive-v0.2"]
    probe = deepcopy(settings)
    # First resolve the installed selection, then bind the fixture to that exact file.
    descriptor = probe["context"]["fontMetrics"]
    descriptor["contentIdentity"] = "sha256:" + "1" * 64
    with pytest.raises(PresentationSettingsError, match="E_FONT_METRICS_UNAVAILABLE"):
        resolve_font_metrics(probe["theme"]["fontFamily"], descriptor)
    import subprocess
    from pathlib import Path
    path = Path(subprocess.run(["fc-match", "-f", "%{file}", "Nimbus Sans"], capture_output=True, text=True, check=True).stdout)
    descriptor["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    metrics = resolve_font_metrics(probe["theme"]["fontFamily"], descriptor)
    assert metrics.width("Chrona", 20) == metrics.width("Chrona", 20)
    assert metrics.width("Chrona", 20) > 0
