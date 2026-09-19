from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from chrona.presentation_settings import PresentationSettingsError, builtin_bases, resolve_presentation_settings


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    path = ROOT / "timeline-design" / "docs" / "fixtures" / name
    return yaml.safe_load(path.read_text()) if path.suffix in {".yaml", ".yml"} else json.loads(path.read_text())


def test_complete_settings_are_resolved_without_mutation():
    value = fixture("presentation-settings-executive-v0.2.json")
    before = deepcopy(value)
    assert resolve_presentation_settings(value) == value
    assert value == before


def test_fixed_base_and_partial_override_are_resolved():
    value = fixture("presentation-preset-override-v0.2.yaml")
    resolved = resolve_presentation_settings(value)
    assert resolved["context"]["locale"] == "ja-JP"
    assert resolved["theme"]["bar"]["radius"] == 0
    assert resolved["theme"]["typography"]["heading"]["size"] == 40


@pytest.mark.parametrize("mutate, diagnostic", [
    (lambda value: value.update(version="unknown"), "E_PRESENTATION_SETTINGS_REQUIRED"),
    (lambda value: value["base"].update(id="gone"), "E_PRESENTATION_REFERENCE"),
    (lambda value: value["overrides"]["theme"]["bar"].update(radius=None), "E_PRESENTATION_PRESET_SCHEMA"),
])
def test_invalid_authoring_resources_are_rejected(mutate, diagnostic):
    value = fixture("presentation-preset-override-v0.2.yaml")
    mutate(value)
    with pytest.raises(PresentationSettingsError, match=diagnostic):
        resolve_presentation_settings(value)


def test_bases_are_data_not_renderer_defaults():
    bases = builtin_bases()
    bases["executive-v0.2"]["theme"]["bar"]["radius"] = 7
    value = fixture("presentation-preset-override-v0.2.yaml")
    value["overrides"].pop("theme")
    assert resolve_presentation_settings(value, bases=bases)["theme"]["bar"]["radius"] == 7
