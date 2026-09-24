"""Safe, identity-neutral access to declared font resource providers."""
from __future__ import annotations

from importlib.metadata import entry_points
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any


class FontResourceError(ValueError):
    """A declared font locator cannot be resolved safely."""


def resolve_font_resource(locator: Any, *, asset_root: Path | None) -> Path:
    """Resolve one schema-validated local or registered-package asset locator."""
    if not isinstance(locator, dict):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    provider, address = locator.get("provider"), locator.get("address")
    if not isinstance(provider, str) or not isinstance(address, str):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    relative = PurePosixPath(address)
    if (not address or relative.is_absolute() or address != relative.as_posix()
            or any(part in {"", ".", ".."} for part in relative.parts)):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    if provider == "context":
        if asset_root is None:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
        candidate = (asset_root.resolve() / Path(*relative.parts)).resolve()
        if candidate != asset_root.resolve() and asset_root.resolve() not in candidate.parents:
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
        if not candidate.is_file():
            raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
        return candidate
    if provider != "package" or not isinstance(locator.get("identity"), str):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    root = _package_root(locator["identity"])
    resource = root.joinpath(*relative.parts)
    if not resource.is_file():
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    return Path(str(resource))


def _package_root(identity: str):
    if identity == "chrona.resources":
        return files("chrona.resources")
    matches = entry_points(group="chrona.font-resource-provider", name=identity)
    if len(matches) != 1:
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    root = matches[0].load()()
    if not hasattr(root, "joinpath"):
        raise FontResourceError("E_FONT_METRICS_UNAVAILABLE")
    return root
