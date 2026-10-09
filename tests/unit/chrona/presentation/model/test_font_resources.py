from pathlib import Path

import pytest

from chrona.presentation.model import font_resources
from chrona.presentation.model.font_resources import FontResourceError, resolve_font_resource


@pytest.mark.parametrize("locator,asset_root,operand", [
    (None, None, "/locator must be an object; found NoneType"),
    ({"provider": "context", "address": 7}, None, "address=7"),
    ({"provider": "context", "address": "../outside.ttf"}, None, "../outside.ttf"),
    ({"provider": "context", "address": "faces/regular.ttf"}, None, "requires an asset_root"),
    ({"provider": "context", "address": "faces/regular.ttf"}, Path("."), "does not name a file"),
    ({"provider": "cloud", "identity": 7, "address": "faces/regular.ttf"}, None, "expected package provider"),
    ({"provider": "package", "identity": "chrona.resources", "address": "fonts/not-packaged.ttf"}, None, "chrona.resources"),
])
def test_resource_error_details_name_locator_field_and_expected_state(locator, asset_root, operand):
    with pytest.raises(FontResourceError, match="E_FONT_METRICS_UNAVAILABLE") as error:
        resolve_font_resource(locator, asset_root=asset_root)
    assert error.value.diagnostic_id == "E_FONT_METRICS_UNAVAILABLE"
    assert operand in error.value.detail
    assert "E_FONT_METRICS_UNAVAILABLE" in str(error.value)


class _BrokenResolver:
    def resolve_asset(self, locator, expected_identity):
        raise FileNotFoundError("private path text is not surfaced")


def test_custom_resolver_failure_names_provider_identity_and_address_without_exception_text():
    locator = {"provider": "context", "identity": "local-context", "address": "fonts/regular.ttf"}
    with pytest.raises(FontResourceError) as error:
        resolve_font_resource(locator, asset_root=None, asset_resolver=_BrokenResolver())
    assert "provider='context'" in error.value.detail
    assert "identity='local-context'" in error.value.detail
    assert "fonts/regular.ttf" in error.value.detail
    assert "FileNotFoundError" in error.value.detail
    assert "private path text" not in error.value.detail


def test_package_provider_lookup_failure_reports_identity_and_match_count(monkeypatch):
    monkeypatch.setattr(font_resources, "entry_points", lambda **kwargs: ())
    with pytest.raises(FontResourceError) as error:
        resolve_font_resource(
            {"provider": "package", "identity": "chrona.no-provider", "address": "fonts/a.ttf"},
            asset_root=None,
        )
    assert "chrona.no-provider" in error.value.detail
    assert "found 0 entry points" in error.value.detail


def test_package_provider_root_contract_names_returned_type(monkeypatch):
    class _EntryPoint:
        def load(self):
            return lambda: 17

    monkeypatch.setattr(font_resources, "entry_points", lambda **kwargs: (_EntryPoint(),))
    with pytest.raises(FontResourceError) as error:
        resolve_font_resource(
            {"provider": "package", "identity": "custom-fonts", "address": "fonts/a.ttf"},
            asset_root=None,
        )
    assert "custom-fonts" in error.value.detail
    assert "Traversable resource root" in error.value.detail and "int" in error.value.detail
