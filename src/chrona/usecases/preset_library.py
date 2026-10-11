"""Copy finite builtin presentation presets into editable local Draft source."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from hashlib import sha256
from typing import Any

import yaml

from chrona.core.store_address import StoreAddressError, check_store_address
from chrona.resources import builtin_preset_library_resource, builtin_preset_source_root, safe_load, schema_validator
from chrona.presentation.contracts import ClosureIdentity, IconCatalogContract, parse_contract
from chrona.usecases.failure_report import StableFailure


DEFAULT_PRESET_ID = "chrona-default-draft"
"""The bundled look `chrona render` uses without `--preset`; it is also a catalogue entry, so it can be listed and copied (#1305)."""


class _PlainDumper(yaml.SafeDumper):
    """A dumper that never writes anchors or aliases: every repeated mapping is written in full."""

    def ignore_aliases(self, data: object) -> bool:
        return True


def _safe(address: object) -> str:
    """Return a catalogue address the shared Store-address guard accepts (the schema's `storeAddress`), else refuse (#731)."""
    try:
        check_store_address(address)
    except StoreAddressError as error:
        raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: catalogue address {address!r} is not a safe relative address") from error
    return address  # type: ignore[return-value]


def _library() -> list[dict[str, Any]]:
    try:
        value = safe_load(builtin_preset_library_resource().read_bytes())
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"E_BUILTIN_PRESET_LIBRARY: presets/library.yaml cannot be read: {error}") from error
    if not isinstance(value, dict) or tuple(schema_validator("preset-library-v0.2.schema.yaml").iter_errors(value)):
        raise ValueError("E_BUILTIN_PRESET_LIBRARY: presets/library.yaml does not satisfy preset-library-v0.2.schema.yaml")
    entries = value["entries"]
    if not isinstance(entries, list) or len({item.get("id") for item in entries if isinstance(item, dict)}) != len(entries):
        raise ValueError("E_BUILTIN_PRESET_LIBRARY: presets/library.yaml declares a preset id twice")
    for entry in entries:
        members = entry.get("members", {})
        catalogs = members.get("iconCatalogs", []) if isinstance(members, dict) else []
        identifiers = [member.get("id") for member in catalogs if isinstance(member, dict)]
        if len(identifiers) != len(catalogs) or len(set(identifiers)) != len(identifiers):
            raise ValueError(f"E_BUILTIN_PRESET_LIBRARY: preset {entry.get('id')!r} declares an icon catalog without an id or with a repeated id")
    return entries


_MEMBER_OUTPUTS = {
    "view": "view.yaml",
    "theme": "theme.yaml",
    "colorScheme": "scheme.yaml",
    "layout": "layout.yaml",
}


def _member(entry: dict[str, Any], name: str) -> dict[str, Any]:
    members = entry.get("members")
    value = members.get(name) if isinstance(members, dict) else None
    if not isinstance(value, dict):
        raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: preset {entry.get('id')!r} declares no {name!r} member")
    return value


def _read_member(member: dict[str, Any]) -> bytes:
    source = builtin_preset_source_root(_safe(member.get("sourceRoot")))
    address = _safe(member.get("sourcePath"))
    item = source.joinpath(*PurePosixPath(address).parts)
    try:
        raw = item.read_bytes()
    except OSError as error:
        raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: member {member.get('id')!r} cannot be read at {address}: {error}") from error
    expected_identity = member.get("contentIdentity")
    if expected_identity is not None and sha256(raw).hexdigest() != str(expected_identity).removeprefix("sha256:"):
        raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: member {member.get('id')!r} at {address} does not match its declared content identity")
    value = safe_load(raw)
    if not isinstance(value, dict) or value.get("id") != member.get("id"):
        raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: the document at {address} is not a mapping with id {member.get('id')!r}")
    # Layout Profile and review-detail documents intentionally identify their
    # contract through `version`, unlike presentation resources which also carry `kind`.
    if member.get("kind") not in {"layout-profile", "review-detail-profile"} and value.get("kind") != member.get("kind"):
        raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: the document at {address} has kind {value.get('kind')!r}, the catalogue declares {member.get('kind')!r}")
    return raw


def list_builtin_presets() -> list[dict[str, str]]:
    """Return the finite catalogue's id/gallerySet pairs, in `library.yaml` order (#429)."""
    return [{"id": str(entry["id"]), "gallerySet": str(entry["gallerySet"])} for entry in _library()]


def is_builtin_preset_id(identifier: str) -> bool:
    """Return whether `identifier` names a catalogue entry, without loading its members (#429)."""
    return any(entry.get("id") == identifier for entry in _library())


def copy_builtin_preset(identifier: str, destination: Path) -> Path:
    """Materialize one project-generic builtin preset as editable local files."""
    entry = next((item for item in _library() if item.get("id") == identifier), None)
    if entry is None:
        raise StableFailure(
            "E_BUILTIN_PRESET_UNKNOWN",
            f"unknown builtin preset {identifier!r}; valid ids: "
            + ", ".join(str(item["id"]) for item in _library())
            + " (chrona preset list); a value containing '/' or ending in .yaml is read as a file path",
            "presentation",
        )
    if destination.exists() and any(destination.iterdir()):
        raise StableFailure(
            "E_BUILTIN_PRESET_OUTPUT_EXISTS",
            f"output directory {destination} already exists and is not empty; copy to a new directory",
            "presentation",
        )
    # Fully preflight every declared byte before creating the destination or
    # writing the first member. This keeps failures atomic at the copy boundary.
    payloads: dict[str, bytes] = {}
    resources: dict[str, Any] = {}
    for name, output in _MEMBER_OUTPUTS.items():
        member = _member(entry, name)
        payloads[output] = _read_member(member)
        resources[name] = {"id": str(member["id"]), "kind": str(member["kind"]), "path": output}
    if isinstance(entry.get("members"), dict) and "detailProfile" in entry["members"]:
        member = _member(entry, "detailProfile")
        payloads["detail.yaml"] = _read_member(member)
        resources["detailProfile"] = {"id": str(member["id"]), "kind": str(member["kind"]), "path": "detail.yaml"}
    members_value = entry.get("members", {})
    for member in members_value.get("iconCatalogs", []) if isinstance(members_value, dict) else []:
        raw = _read_member(member)
        try:
            catalog = parse_contract(ClosureIdentity("icon-catalog", str(member["id"]), "builtin", str(member["contentIdentity"])), safe_load(raw))
            if not isinstance(catalog, IconCatalogContract) or catalog.identity.id != member["id"]:
                raise ValueError
        except Exception as error:
            raise ValueError(f"E_BUILTIN_PRESET_RESOURCE: icon catalog {member['id']!r} is not a valid icon catalog with that id") from error
        source = builtin_preset_source_root(_safe(member.get("sourceRoot")))
        notice_path = _safe(member.get("noticeSourcePath"))
        try:
            notice = source.joinpath(*PurePosixPath(notice_path).parts).read_bytes()
        except OSError as error:
            raise ValueError(f"E_BUILTIN_PRESET_NOTICE: the notice {notice_path} of icon catalog {member['id']!r} cannot be read: {error}") from error
        if sha256(notice).hexdigest() != str(member.get("noticeContentIdentity", "")).removeprefix("sha256:"):
            raise ValueError(f"E_BUILTIN_PRESET_NOTICE: the notice {notice_path} does not match its declared content identity")
        license_value = catalog.provenance.get("license")
        declared = license_value.get("notice") if hasattr(license_value, "get") else None
        if not isinstance(declared, str) or notice != declared.encode("utf-8"):
            raise ValueError(f"E_BUILTIN_PRESET_NOTICE: the notice {notice_path} differs from the license notice in the provenance of icon catalog {member['id']!r}")
        output = f"catalogs/{member['id']}.yaml"
        notice_output = f"catalogs/{member['id']}.NOTICE"
        payloads[output] = raw
        payloads[notice_output] = notice
        resources.setdefault("iconCatalogs", []).append({"id": member["id"], "kind": "icon-catalog", "path": output})
    destination.mkdir(parents=True, exist_ok=True)
    for output, raw in payloads.items():
        target = destination / output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    scheme = resources["colorScheme"]
    preset: dict[str, Any] = {
        "version": "chrona/presentation-preset/v0.1",
        "kind": "presentation-preset",
        "id": f"chrona-builtin-{identifier}",
        "body": {
            "package": {"version": "1"},
            "resources": resources,
            "compatibleColorSchemes": [scheme],
        },
    }
    if isinstance(entry.get("visualProfile"), dict):
        preset["body"]["visualProfile"] = {"preferred": str(entry["visualProfile"]["preferred"])}
    preset_target = destination / "preset.yaml"
    preset_target.write_text(yaml.dump(preset, Dumper=_PlainDumper, sort_keys=False), encoding="utf-8")
    return preset_target
