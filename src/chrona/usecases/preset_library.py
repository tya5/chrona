"""Copy finite builtin presentation presets into editable local Draft source."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from chrona.resources import builtin_preset_library_resource, builtin_preset_source_root, safe_load, schema_document


def _safe(address: object) -> str:
    if not isinstance(address, str):
        raise ValueError("E_BUILTIN_PRESET_RESOURCE")
    path = PurePosixPath(address)
    if (not address or path.is_absolute() or address != path.as_posix()
            or any(part in {"", ".", ".."} for part in path.parts)):
        raise ValueError("E_BUILTIN_PRESET_RESOURCE")
    return address


def _library() -> list[dict[str, Any]]:
    try:
        value = safe_load(builtin_preset_library_resource().read_bytes())
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("E_BUILTIN_PRESET_LIBRARY") from error
    schema = schema_document("preset-library-v0.1.schema.yaml")
    if not isinstance(value, dict) or tuple(Draft202012Validator(schema).iter_errors(value)):
        raise ValueError("E_BUILTIN_PRESET_LIBRARY")
    entries = value["entries"]
    if not isinstance(entries, list) or len({item.get("id") for item in entries if isinstance(item, dict)}) != len(entries):
        raise ValueError("E_BUILTIN_PRESET_LIBRARY")
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
        raise ValueError("E_BUILTIN_PRESET_RESOURCE")
    return value


def _copy_member(member: dict[str, Any], destination: Path, output: str) -> dict[str, str]:
    source = builtin_preset_source_root(_safe(member.get("sourceRoot")))
    address = _safe(member.get("sourcePath"))
    item = source.joinpath(*PurePosixPath(address).parts)
    if not item.is_file():
        raise ValueError("E_BUILTIN_PRESET_RESOURCE")
    value = safe_load(item.read_bytes())
    if not isinstance(value, dict) or value.get("id") != member.get("id"):
        raise ValueError("E_BUILTIN_PRESET_RESOURCE")
    # Layout Profile and review-detail documents intentionally identify their
    # contract through `version`, unlike presentation resources which also carry `kind`.
    if member.get("kind") not in {"layout-profile", "review-detail-profile"} and value.get("kind") != member.get("kind"):
        raise ValueError("E_BUILTIN_PRESET_RESOURCE")
    target = destination / output
    target.write_bytes(item.read_bytes())
    return {"id": str(member["id"]), "kind": str(member["kind"]), "path": output}


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
        raise ValueError("E_BUILTIN_PRESET_UNKNOWN")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("E_BUILTIN_PRESET_OUTPUT_EXISTS")
    destination.mkdir(parents=True, exist_ok=True)
    resources = {
        name: _copy_member(_member(entry, name), destination, output)
        for name, output in _MEMBER_OUTPUTS.items()
    }
    if isinstance(entry.get("members"), dict) and "detailProfile" in entry["members"]:
        resources["detailProfile"] = _copy_member(_member(entry, "detailProfile"), destination, "detail.yaml")
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
    preset_target.write_text(yaml.safe_dump(preset, sort_keys=False), encoding="utf-8")
    return preset_target
