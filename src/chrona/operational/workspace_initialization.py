"""Exclusive publication boundary for a new guided workspace directory."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Mapping

from chrona.core.store_address import StoreAddressError, check_store_address


def publish_workspace_directory(destination: Path, files: Mapping[str, bytes]) -> None:
    """Create a new directory, publish its resources, and write workspace.yaml last.

    This is an exclusive new-directory operation, not an atomic directory rename.
    The destination becomes visible while its files are being written, but it is
    not a usable workspace until initialization completes.
    """
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"E_AUTHORING_WORKSPACE_EXISTS: destination {destination} already exists")
    parent = destination.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError(f"E_WORKSPACE_PARENT: destination parent {parent} must be an existing real directory")
    normalized: dict[str, bytes] = {}
    for name, payload in files.items():
        if not isinstance(name, str) or not isinstance(payload, bytes):
            raise TypeError("workspace files must map relative paths to bytes")
        try:
            check_store_address(name)
        except StoreAddressError as error:
            raise ValueError(f"E_WORKSPACE_FILE_PATH: {name!r} is not a safe relative path") from error
        path = PurePosixPath(name)
        if path.as_posix() != name or name in normalized:
            raise ValueError(f"E_WORKSPACE_FILE_PATH: {name!r} is not a canonical relative path")
        normalized[name] = payload
    if "workspace.yaml" not in normalized:
        raise ValueError("E_WORKSPACE_FILE_SET: workspace.yaml is required")

    created_files: list[tuple[Path, int, int]] = []
    created_dirs: list[tuple[Path, int, int]] = []
    destination_identity: tuple[int, int] | None = None
    try:
        destination.mkdir()
        destination_stat = destination.lstat()
        destination_identity = (destination_stat.st_dev, destination_stat.st_ino)
        for name, payload in sorted(normalized.items(), key=lambda item: (item[0] == "workspace.yaml", item[0])):
            target = destination.joinpath(*PurePosixPath(name).parts)
            directory = target.parent
            missing: list[Path] = []
            cursor = directory
            while cursor != destination and not cursor.exists():
                missing.append(cursor)
                cursor = cursor.parent
            for path in reversed(missing):
                path.mkdir()
                stat = path.lstat()
                created_dirs.append((path, stat.st_dev, stat.st_ino))
            if target.exists() or target.is_symlink():
                raise FileExistsError(f"E_WORKSPACE_FILE_COLLISION: {name!r} appeared during publication")
            with target.open("xb") as handle:
                stat = os.fstat(handle.fileno())
                created_files.append((target, stat.st_dev, stat.st_ino))
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
    except BaseException:
        _remove_owned(destination, destination_identity, created_files, created_dirs)
        raise


def _remove_owned(
    destination: Path,
    destination_identity: tuple[int, int] | None,
    created_files: list[tuple[Path, int, int]],
    created_dirs: list[tuple[Path, int, int]],
) -> None:
    for path, device, inode in reversed(created_files):
        try:
            stat = path.lstat()
            if (stat.st_dev, stat.st_ino) == (device, inode) and path.is_file() and not path.is_symlink():
                path.unlink()
        except OSError:
            pass
    for path, device, inode in reversed(created_dirs):
        try:
            stat = path.lstat()
            if (stat.st_dev, stat.st_ino) == (device, inode) and path.is_dir() and not path.is_symlink():
                path.rmdir()
        except OSError:
            pass
    if destination_identity is not None:
        try:
            stat = destination.lstat()
            if ((stat.st_dev, stat.st_ino) == destination_identity
                    and destination.is_dir() and not destination.is_symlink()):
                destination.rmdir()
        except OSError:
            pass
