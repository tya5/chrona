"""The one place a Store address becomes a filesystem path (#710).

A Store address arrives in a document or a command, so it is untrusted text.
Every adapter that opens or creates a file from one calls ``resolve_store_address``
(or ``check_store_address`` when it only needs the segments); none of them joins the
text to a path itself. The syntax decision consults both ``PurePosixPath`` and
``PureWindowsPath`` and never the host path flavour, so an address is accepted or
refused identically on every operating system: a Windows drive or backslash form is
refused on Linux too, and is unit-testable there.

A Store address is also held to the schema's ``storeAddress`` (#731): segments of ``[A-Za-z0-9._-]`` and no all-dot
segment, so the guard never accepts what the schema refuses. A caller that joins an identifier or an operator's file
name, not an address, asks for ``charset="file-name"`` explicitly and keeps the wider set it always accepted.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath
import re
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


_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")


def _has_foreign_segment(segments: tuple[str, ...]) -> bool:
    """A segment outside the ``storeAddress`` grammar: a character other than ``[A-Za-z0-9._-]``, or only dots.

    ``fullmatch`` with an explicit ASCII class, never ``$`` (which lets a trailing newline through) and never
    ``\\w`` or ``str.isalnum`` (which accept non-ASCII letters), so the verdict equals the schema's on every string.
    """
    return any(_SEGMENT.fullmatch(segment) is None or not segment.strip(".") for segment in segments)


# What a caller means by its text. ``address`` is a Store address and follows the schema's ``storeAddress``
# exactly. ``file-name`` is for a caller that joins an identifier or an operator's file name, not an address,
# and legitimately accepts a wider character set (spaces, non-ASCII): the workspace file name of the authoring
# commands (the schema's ``fileName``) and the Actual Set id used as an adapter-private tip file name.
Charset = Literal["address", "file-name"]


def check_store_address(address: object, *, charset: Charset = "address") -> tuple[str, ...]:
    """Return the address's ``/`` separated segments, or raise ``StoreAddressError("syntax")``.

    Pure: no filesystem access, the same answer on every OS. An address is refused when it
    is not a non-empty ``str``; contains a backslash, a colon, NUL or any control character;
    has a drive, root or anchor under either ``PurePosixPath`` or ``PureWindowsPath``; or has
    an empty segment or a segment made only of dots and spaces (``.``, ``..``, ``...``).
    With the default ``charset="address"`` it also refuses any character outside
    ``[A-Za-z0-9._-]`` and any all-dot segment, so the verdict is the schema's ``storeAddress``.
    ``charset="file-name"`` keeps only the checks above (see ``Charset``).
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
    if charset == "address" and _has_foreign_segment(segments):
        raise StoreAddressError("syntax", address, "has a character outside letters, digits, '.', '_' and '-'")
    return segments


def check_store_segment(name: object, *, charset: Charset = "address") -> str:
    """Return ``name`` when it is a single safe segment (an identifier used as a file name), else raise."""
    if len(check_store_address(name, charset=charset)) != 1:
        raise StoreAddressError("syntax", name, "expected one segment, found a separator")
    return name  # type: ignore[return-value]


def resolve_store_address(base: Path, address: object, *, root: Path | None = None, charset: Charset = "address") -> Path:
    """Return the resolved path of ``address`` under ``base``, or raise ``StoreAddressError``.

    The address must pass ``check_store_address`` and the resolved target (symlinks
    followed) must lie strictly inside ``(root or base).resolve()``. ``root`` is the Store
    root when ``base`` is a directory below it (a revision directory). The resolved path is
    returned so the caller opens exactly what was checked.
    """
    segments = check_store_address(address, charset=charset)
    try:
        boundary = (base if root is None else root).resolve()
        target = base.resolve().joinpath(*segments).resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise StoreAddressError("containment", address, f"cannot resolve: {type(error).__name__}") from error
    if target == boundary or not target.is_relative_to(boundary):
        raise StoreAddressError("containment", address, "resolves outside the Store root")
    return target
