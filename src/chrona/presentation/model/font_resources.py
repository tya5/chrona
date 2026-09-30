"""Safe, identity-neutral access to declared font resource providers."""
from __future__ import annotations

from importlib.metadata import entry_points
from importlib.resources import files
from pathlib import Path
from typing import Any, Protocol

from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address


class FontResourceError(ValueError):
    """A declared font locator cannot be resolved safely."""


class FontAssetResolver(Protocol):
    def resolve_asset(self, locator: dict[str, Any], expected_identity: str | None) -> Path: ...


def resolve_font_resource(locator: Any, *, asset_root: Path | None,
                          asset_resolver: FontAssetResolver | None = None,
                          expected_identity: str | None = None) -> Path:
    """Resolve one schema-validated local or registered-package asset locator."""
    if not isinstance(locator, dict):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    provider, address = locator.get("provider"), locator.get("address")
    if not isinstance(provider, str) or not isinstance(address, str):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    try:
        segments = check_store_address(address)
    except StoreAddressError as error:
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE") from error
    if asset_resolver is not None:
        try:
            return asset_resolver.resolve_asset(locator, expected_identity)
        except (KeyError, OSError, ValueError) as error:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE") from error
    if provider == "context":
        if asset_root is None:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
        try:
            candidate = resolve_store_address(asset_root, address)
        except StoreAddressError as error:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE") from error
        if not candidate.is_file():
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
        return candidate
    if provider != "package" or not isinstance(locator.get("identity"), str):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    root = _package_root(locator["identity"])
    resource = root.joinpath(*segments)
    if not resource.is_file():
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    return Path(str(resource))


def _package_root(identity: str):
    if identity == "chrona.resources":
        return files("chrona.resources")
    matches = tuple(entry_points(group="chrona.font-resource-provider", name=identity))
    if len(matches) != 1:
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    root = matches[0].load()()
    if not hasattr(root, "joinpath"):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    return root
