"""Validation for declarative presentation package source trees.

This module validates a package before acquisition.  It deliberately has no
dependency on authoring normalization, Context resolution, Layout, Scene, or a
renderer.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, PresentationPresetContract, parse_contract
from chrona.resources import schema_resource


class PackageError(ValueError):
    """A presentation package cannot become an immutable acquisition input."""


@dataclass(frozen=True)
class PackageMember:
    id: str
    kind: str
    path: str
    content_identity: str


@dataclass(frozen=True)
class PresentationPackage:
    id: str
    release: str
    content_identity: str
    publisher_id: str
    license: str
    presets: tuple[PackageMember, ...]
    resources: tuple[PackageMember, ...]
    compatibility: Mapping[str, Any]

    def member(self, path: str) -> PackageMember | None:
        return next((item for item in (*self.presets, *self.resources) if item.path == path), None)


def verify_presentation_package(root: Path) -> PresentationPackage:
    """Verify one complete source tree and return its immutable manifest view."""
    root = root.resolve()
    manifest_path = root / "package.yaml"
    if not root.is_dir() or not manifest_path.is_file() or manifest_path.is_symlink():
        raise PackageError("E_PACKAGE_MANIFEST")
    manifest = _load_manifest(manifest_path)
    presets = tuple(_member(item, "presentation-preset") for item in manifest["members"]["presets"])
    resources = tuple(_member(item, str(item["kind"])) for item in manifest["members"]["resources"])
    members = (*presets, *resources)
    if len({item.path for item in members}) != len(members) or len({(item.kind, item.id) for item in members}) != len(members):
        raise PackageError("E_PACKAGE_MEMBER_DUPLICATE")
    _verify_paths_and_bytes(root, members)
    expected = package_content_identity(manifest, root, members)
    if manifest["package"]["contentIdentity"] != expected:
        raise PackageError("E_PACKAGE_CONTENT_IDENTITY")
    package = PresentationPackage(str(manifest["id"]), str(manifest["package"]["release"]), expected,
                                  str(manifest["package"]["publisher"]["id"]), str(manifest["package"]["license"]),
                                  presets, resources, manifest["compatibility"])
    _verify_member_contracts(root, package)
    return package


def package_content_identity(manifest: Mapping[str, Any], root: Path, members: tuple[PackageMember, ...]) -> str:
    """Return the Spec 62 framed aggregate identity without self-reference."""
    canonical = _without_identity(manifest)
    digest = sha256()
    _frame(digest, b"manifest", json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    for member in sorted(members, key=lambda item: item.path):
        _frame(digest, member.path.encode("utf-8"), _child(root, member.path).read_bytes())
    return "sha256:" + digest.hexdigest()


def _frame(digest: Any, name: bytes, payload: bytes) -> None:
    digest.update(len(name).to_bytes(8, "big")); digest.update(name)
    digest.update(len(payload).to_bytes(8, "big")); digest.update(payload)


def _without_identity(manifest: Mapping[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(manifest))
    del value["package"]["contentIdentity"]
    return value


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_bytes())
    except yaml.YAMLError as error:
        raise PackageError("E_PACKAGE_MANIFEST") from error
    if not isinstance(value, dict):
        raise PackageError("E_PACKAGE_MANIFEST")
    schema = yaml.safe_load(schema_resource("presentation-package-v0.1.schema.yaml").read_text(encoding="utf-8"))
    if tuple(jsonschema.Draft202012Validator(schema).iter_errors(value)):
        raise PackageError("E_PACKAGE_MANIFEST")
    return value


def _member(value: Mapping[str, Any], kind: str) -> PackageMember:
    return PackageMember(str(value["id"]), kind, str(value["path"]), str(value["contentIdentity"]))


def _verify_paths_and_bytes(root: Path, members: tuple[PackageMember, ...]) -> None:
    allowed_prefix = {"presentation-preset": "presets/", "view": "views/", "layout-profile": "layouts/",
                      "theme": "themes/", "color-scheme": "schemes/"}
    declared = {"package.yaml", *(item.path for item in members)}
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise PackageError("E_PACKAGE_SYMLINK")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != declared:
        raise PackageError("E_PACKAGE_UNDECLARED_FILE")
    for member in members:
        if not member.path.startswith(allowed_prefix[member.kind]):
            raise PackageError("E_PACKAGE_MEMBER_PATH")
        payload = _child(root, member.path).read_bytes()
        if "sha256:" + sha256(payload).hexdigest() != member.content_identity:
            raise PackageError("E_PACKAGE_MEMBER_IDENTITY")


def _child(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file() or path.is_symlink():
        raise PackageError("E_PACKAGE_MEMBER_PATH")
    return path


def _verify_member_contracts(root: Path, package: PresentationPackage) -> None:
    resources = {(item.kind, item.id, item.path): item for item in package.resources}
    for member in package.resources:
        document = _yaml_member(root, member)
        try:
            parse_contract(ClosureIdentity(member.kind, member.id, package.release, member.content_identity), document)
        except ContractError as error:
            raise PackageError("E_PACKAGE_MEMBER_SCHEMA") from error
    for member in package.presets:
        document = _yaml_member(root, member)
        try:
            contract = parse_contract(ClosureIdentity(member.kind, member.id, package.release, member.content_identity), document)
        except ContractError as error:
            raise PackageError("E_PACKAGE_PRESET_SCHEMA") from error
        if not isinstance(contract, PresentationPresetContract) or contract.package_version != package.release:
            raise PackageError("E_PACKAGE_PRESET_IDENTITY")
        declarations = (*contract.resources.values(), *contract.compatible_color_schemes)
        if any((str(item["kind"]), str(item["id"]), str(item["path"])) not in resources for item in declarations):
            raise PackageError("E_PACKAGE_PRESET_MEMBER")


def _yaml_member(root: Path, member: PackageMember) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(_child(root, member.path).read_bytes())
    except yaml.YAMLError as error:
        raise PackageError("E_PACKAGE_MEMBER_SCHEMA") from error
    if not isinstance(value, Mapping) or value.get("id") != member.id:
        raise PackageError("E_PACKAGE_MEMBER_SCHEMA")
    return value
