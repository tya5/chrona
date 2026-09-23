"""Explicit local presentation-package acquisition and immutable lock records."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import jsonschema
import yaml

from chrona.presentation.packages import PackageError, PresentationPackage, verify_presentation_package
from chrona.resources import schema_resource


class AcquisitionError(ValueError):
    """An explicit package acquisition or locked-byte verification failed."""


@dataclass(frozen=True)
class AcquiredPackage:
    package: PresentationPackage
    preset_id: str
    lock: Mapping[str, Any]


def acquire_local_package(*, source_root: Path, cache_root: Path, preset_id: str, lock_path: Path) -> AcquiredPackage:
    """Verify/copy one local package, then atomically replace its lock record."""
    try:
        package = verify_presentation_package(source_root)
    except PackageError as error:
        raise AcquisitionError(str(error)) from error
    preset = next((item for item in package.presets if item.id == preset_id), None)
    if preset is None:
        raise AcquisitionError("E_PACKAGE_ACQUIRE_PRESET")
    destination = cache_package_root(cache_root, package)
    if destination.exists():
        try:
            cached = verify_presentation_package(destination)
        except PackageError as error:
            raise AcquisitionError("E_PACKAGE_CACHE_CORRUPT") from error
        if cached.content_identity != package.content_identity:
            raise AcquisitionError("E_PACKAGE_CACHE_CONFLICT")
    else:
        _copy_verified(source_root.resolve(), destination)
        try:
            if verify_presentation_package(destination).content_identity != package.content_identity:
                raise AcquisitionError("E_PACKAGE_CACHE_CORRUPT")
        except PackageError as error:
            raise AcquisitionError("E_PACKAGE_CACHE_CORRUPT") from error
    lock = _lock(package, preset_id, source_root)
    _write_lock(lock_path, lock)
    return AcquiredPackage(package, preset_id, lock)


def cache_package_root(cache_root: Path, package: PresentationPackage) -> Path:
    """Deterministic local lookup; this cache address is not serialized in a lock."""
    namespace, name = package.id.split("/", 1)
    return cache_root.resolve() / namespace / name / package.release / package.content_identity.removeprefix("sha256:")


def verify_locked_package(*, cache_root: Path, lock: Mapping[str, Any], package_id: str, preset_id: str) -> AcquiredPackage:
    """Verify the exact cached bytes named by a lock without any acquisition lookup."""
    _validate_lock(lock)
    entry = next((item for item in lock["packages"] if item["id"] == package_id), None)
    if entry is None or preset_id not in entry["presets"]:
        raise AcquisitionError("E_PACKAGE_LOCK_PIN")
    provisional = _locked_package(entry)
    root = cache_package_root(cache_root, provisional)
    if not root.is_dir():
        raise AcquisitionError("E_PACKAGE_OFFLINE_UNAVAILABLE")
    try:
        package = verify_presentation_package(root)
    except PackageError as error:
        raise AcquisitionError("E_PACKAGE_LOCK_BYTES") from error
    expected = _lock(package, preset_id, root)
    if json.dumps(expected, sort_keys=True) != json.dumps({"version": lock["version"], "packages": [entry]}, sort_keys=True):
        raise AcquisitionError("E_PACKAGE_LOCK_BYTES")
    return AcquiredPackage(package, preset_id, lock)


def _locked_package(entry: Mapping[str, Any]) -> PresentationPackage:
    # Only ID/release/content identity are needed to derive a cache address.
    return PresentationPackage(str(entry["id"]), str(entry["release"]), str(entry["contentIdentity"]), "", "", (), (), entry["compatibility"])


def _lock(package: PresentationPackage, preset_id: str, root: Path) -> dict[str, Any]:
    preset = next(item for item in package.presets if item.id == preset_id)
    raw = yaml.safe_load((root / preset.path).read_bytes())
    declarations = raw["body"]["resources"]
    by_key = {(item.kind, item.id, item.path): item for item in package.resources}
    resources = {}
    for slot, declaration in declarations.items():
        member = by_key[(declaration["kind"], declaration["id"], declaration["path"])]
        resources[slot] = {"id": member.id, "kind": member.kind, "contentIdentity": member.content_identity}
    return {"version": "chrona/package-lock/v0.1", "packages": [{
        "id": package.id, "release": package.release, "contentIdentity": package.content_identity,
        "manifest": {"contentIdentity": package.content_identity},
        "presets": {preset_id: {"contentIdentity": preset.content_identity, "resources": resources}},
        "compatibility": dict(package.compatibility),
    }]}


def _copy_verified(source: Path, destination: Path) -> None:
    if destination.exists():
        raise AcquisitionError("E_PACKAGE_CACHE_CONFLICT")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / "package"
        shutil.copytree(source, staged, symlinks=True)
        staged.rename(destination)


def _write_lock(path: Path, value: Mapping[str, Any]) -> None:
    _validate_lock(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as output:
        output.write(yaml.safe_dump(dict(value), sort_keys=True))
        temporary = Path(output.name)
    temporary.replace(path)


def _validate_lock(value: Mapping[str, Any]) -> None:
    schema = yaml.safe_load(schema_resource("package-lock-v0.1.schema.yaml").read_text(encoding="utf-8"))
    if tuple(jsonschema.Draft202012Validator(schema).iter_errors(value)):
        raise AcquisitionError("E_PACKAGE_LOCK_SCHEMA")
