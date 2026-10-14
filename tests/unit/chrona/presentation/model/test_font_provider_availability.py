"""The typed unavailable-provider fact means exactly zero registered providers."""
from pathlib import Path

import pytest

from chrona.presentation.model import font_resources
from chrona.presentation.model.font_resources import FontProviderUnavailable, FontResourceError, resolve_font_resource


def _locator() -> dict[str, str]:
    return {"provider": "package", "identity": "chrona.test-fonts", "address": "fonts/regular.ttf"}


def test_zero_entry_points_raise_typed_unavailable_provider(monkeypatch):
    monkeypatch.setattr(font_resources, "entry_points", lambda **kwargs: ())

    with pytest.raises(FontProviderUnavailable) as unavailable:
        resolve_font_resource(_locator(), asset_root=None)

    assert unavailable.value.identity == "chrona.test-fonts"
    assert unavailable.value.diagnostic_id == "E_FONT_METRICS_UNAVAILABLE"


def test_duplicate_entry_points_remain_a_hard_resource_error(monkeypatch):
    class _EntryPoint:
        def load(self):
            return lambda: Path(".")

    monkeypatch.setattr(font_resources, "entry_points", lambda **kwargs: (_EntryPoint(), _EntryPoint()))

    with pytest.raises(FontResourceError) as error:
        resolve_font_resource(_locator(), asset_root=None)

    assert not isinstance(error.value, FontProviderUnavailable)
    assert "found 2 entry points" in error.value.detail


def test_invalid_installed_provider_root_remains_a_hard_resource_error(monkeypatch):
    class _EntryPoint:
        def load(self):
            return lambda: 17

    monkeypatch.setattr(font_resources, "entry_points", lambda **kwargs: (_EntryPoint(),))

    with pytest.raises(FontResourceError) as error:
        resolve_font_resource(_locator(), asset_root=None)

    assert not isinstance(error.value, FontProviderUnavailable)
    assert "Traversable resource root" in error.value.detail
