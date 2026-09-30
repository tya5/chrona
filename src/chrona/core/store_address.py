"""The one place a Store address becomes a filesystem path (#710).

A Store address arrives in a document or a command, so it is untrusted text.
Every adapter that opens or creates a file from one calls ``resolve_store_address``
(or ``check_store_address`` when it only needs the segments); none of them joins the
text to a path itself. The syntax decision consults both ``PurePosixPath`` and
``PureWindowsPath`` and never the host path flavour, so an address is accepted or
refused identically on every operating system: a Windows drive or backslash form is
refused on Linux too, and is unit-testable there.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal
import unicodedata


class StoreAddressError(ValueError):
    """An address was refused; ``kind`` says which rule did it."""

    def __init__(self, kind: Literal["syntax", "containment"], address: object, reason: str):
        super().__init__(f"store address {address!r} refused ({kind}): {reason}")
        self.kind = kind
        self.address = address
        self.reason = reason


def _has_forbidden_character(address: str) -> bool:
    return any(character in "\\:" or unicodedata.category(character) == "Cc" for character in address)


def _has_anchor(address: str) -> bool:
    """A drive, root or anchor under either path flavour, whichever one the host happens to be."""
    return any(path.drive or path.root or path.anchor for path in (PurePosixPath(address), PureWindowsPath(address)))


def _has_bad_segment(segments: tuple[str, ...]) -> bool:
    """An empty segment, or one made only of dots and spaces (Win32 strips those, so ``.. `` is ``..``)."""
    return any(not segment.strip(" .") for segment in segments)


def check_store_address(address: object) -> tuple[str, ...]:
    """Return the address's ``/`` separated segments, or raise ``StoreAddressError("syntax")``.

    Pure: no filesystem access, the same answer on every OS. An address is refused when it
    is not a non-empty ``str``; contains a backslash, a colon, NUL or any control character;
    has a drive, root or anchor under either ``PurePosixPath`` or ``PureWindowsPath``; or has
    an empty segment or a segment made only of dots and spaces (``.``, ``..``, ``...``).
    """
    if not isinstance(address, str) or not address:
        raise StoreAddressError("syntax", address, "not a non-empty string")
    if _has_forbidden_character(address):
        raise StoreAddressError("syntax", address, "contains a backslash, colon, NUL or control character")
    if _has_anchor(address):
        raise StoreAddressError("syntax", address, "has a drive, root or anchor")
    segments = tuple(address.split("/"))
    if _has_bad_segment(segments):
        raise StoreAddressError("syntax", address, "has an empty segment or a segment made only of dots")
    return segments


def check_store_segment(name: object) -> str:
    """Return ``name`` when it is a single safe segment (an identifier used as a file name), else raise."""
    if len(check_store_address(name)) != 1:
        raise StoreAddressError("syntax", name, "expected one segment, found a separator")
    return name  # type: ignore[return-value]


def resolve_store_address(base: Path, address: object, *, root: Path | None = None) -> Path:
    """Return the resolved path of ``address`` under ``base``, or raise ``StoreAddressError``.

    The address must pass ``check_store_address`` and the resolved target (symlinks
    followed) must lie strictly inside ``(root or base).resolve()``. ``root`` is the Store
    root when ``base`` is a directory below it (a revision directory). The resolved path is
    returned so the caller opens exactly what was checked.
    """
    segments = check_store_address(address)
    try:
        boundary = (base if root is None else root).resolve()
        target = base.resolve().joinpath(*segments).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise StoreAddressError("containment", address, f"cannot resolve: {type(error).__name__}") from error
    if target == boundary or not target.is_relative_to(boundary):
        raise StoreAddressError("containment", address, "resolves outside the Store root")
    return target
