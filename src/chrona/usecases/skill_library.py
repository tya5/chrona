"""Copy the packaged chrona agent skill into a directory an agent host reads (#142)."""
from __future__ import annotations

from importlib.resources.abc import Traversable
from pathlib import Path

from chrona.core.store_address import StoreAddressError, check_store_address, resolve_store_address
from chrona.resources import skill_resource


def _members(root: Traversable, prefix: tuple[str, ...] = ()) -> list[tuple[str, Traversable]]:
    """Return every file below `root` as a `/` separated relative address, in a stable order."""
    found: list[tuple[str, Traversable]] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        parts = (*prefix, child.name)
        if child.is_dir():
            found.extend(_members(child, parts))
        elif child.is_file():
            found.append(("/".join(parts), child))
    return found


def copy_skill(destination: Path) -> Path:
    """Copy the packaged skill into an absent or empty `destination`; never overwrite.

    Every member is read and every address checked before the destination is created, so a
    refusal leaves nothing behind. Bytes are copied unchanged.
    """
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("E_SKILL_OUTPUT_EXISTS")
    root = skill_resource()
    payloads: list[tuple[str, bytes]] = []
    for address, member in _members(root):
        try:
            check_store_address(address)
        except StoreAddressError as error:
            raise ValueError("E_SKILL_RESOURCE") from error
        payloads.append((address, member.read_bytes()))
    if not any(address == "SKILL.md" for address, _ in payloads):
        raise ValueError("E_SKILL_RESOURCE")
    destination.mkdir(parents=True, exist_ok=True)
    for address, raw in payloads:
        try:
            target = resolve_store_address(destination, address)
        except StoreAddressError as error:
            raise ValueError("E_SKILL_RESOURCE") from error
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return destination
