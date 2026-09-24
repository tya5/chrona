"""Installed font resource providers remain outside the primary wheel."""
from __future__ import annotations

from importlib.resources import files

from chrona.presentation.model.font_metrics import resolve_font_metrics
from chrona.presentation.model.font_resources import resolve_font_resource
from chrona.resources import safe_load


def test_optional_cjk_provider_resolves_its_descriptor_and_metrics():
    descriptor_path = resolve_font_resource(
        {"provider": "package", "identity": "chrona-fonts-noto-cjk", "address": "font-metrics.yaml"},
        asset_root=None,
    )
    descriptor = safe_load(descriptor_path.read_bytes())
    metrics = resolve_font_metrics("Noto Sans JP, sans-serif", descriptor)
    assert metrics.width("コントローラZ", 18) > 0


def test_primary_resource_package_contains_only_the_small_default_faces():
    root = files("chrona.resources")
    assert root.joinpath("fonts", "noto-sans-regular-v1.ttf").is_file()
    assert not root.joinpath("fonts", "noto-sans-cjk-jp-regular-v1.ttf").is_file()
