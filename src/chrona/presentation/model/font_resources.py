"""Safe, identity-neutral access to declared font resource providers."""
from __future__ import annotations

from importlib.metadata import entry_points
from importlib.resources import files
from pathlib import Path
from typing import Any, Protocol

from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address


class FontResourceError(ValueError):
    """A declared font locator cannot be resolved safely."""

    def __init__(self, diagnostic_id: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail


class FontAssetResolver(Protocol):
    def resolve_asset(self, locator: dict[str, Any], expected_identity: str | None) -> Path: ...


def resolve_font_resource(locator: Any, *, asset_root: Path | None,
                          asset_resolver: FontAssetResolver | None = None,
                          expected_identity: str | None = None) -> Path:
    """Resolve one schema-validated local or registered-package asset locator."""
    if not isinstance(locator, dict):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"/locator must be an object; found {type(locator).__name__}")
    provider, address = locator.get("provider"), locator.get("address")
    if not isinstance(provider, str) or not isinstance(address, str):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"/locator/provider and /locator/address must be strings; provider={_shown(provider)}, address={_shown(address)}")
    try:
        segments = check_store_address(address)
    except StoreAddressError as error:
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"/locator/address={_shown(address)} is not a safe store address ({type(error).__name__})") from error
    if asset_resolver is not None:
        try:
            return asset_resolver.resolve_asset(locator, expected_identity)
        except (KeyError, OSError, ValueError) as error:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"provider={_shown(provider)} identity={_shown(locator.get('identity'))} address={_shown(address)} resolver failed ({type(error).__name__})") from error
    if provider == "context":
        if asset_root is None:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"provider=context address={_shown(address)} requires an asset_root")
        try:
            candidate = resolve_store_address(asset_root, address)
        except StoreAddressError as error:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"context address={_shown(address)} cannot be resolved safely ({type(error).__name__})") from error
        if not candidate.is_file():
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"context resource address={_shown(address)} does not name a file")
        return candidate
    if provider != "package" or not isinstance(locator.get("identity"), str):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"/locator/provider={_shown(provider)} and identity={_shown(locator.get('identity'))}; expected package provider with string identity")
    root = _package_root(locator["identity"])
    resource = root.joinpath(*segments)
    if not resource.is_file():
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"package identity={_shown(locator['identity'])} address={_shown(address)} does not name a resource file")
    return Path(str(resource))


def _package_root(identity: str):
    if identity == "chrona.resources":
        return files("chrona.resources")
    matches = tuple(entry_points(group="chrona.font-resource-provider", name=identity))
    if len(matches) != 1:
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"package provider identity={_shown(identity)} must resolve exactly once; found {len(matches)} entry points")
    root = matches[0].load()()
    if not hasattr(root, "joinpath"):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE", f"package provider identity={_shown(identity)} must return a Traversable resource root; got {type(root).__name__}")
    return root


def _shown(value: object) -> str:
    """Show bounded locator operands, never serialize the locator object."""
    if isinstance(value, (str, int, float, bool, type(None))):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    return f"<{type(value).__name__}>"
