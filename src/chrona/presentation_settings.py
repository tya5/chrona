"""Resolution and validation for schema-owned presentation settings v0.2."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


class PresentationSettingsError(ValueError):
    """A stable diagnostic emitted while closing presentation settings."""


_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_DIR = _ROOT / "schemas"
_FIXTURE = _ROOT / "conformance" / "presentation-settings-executive-v0.2.json"
SETTINGS_VERSION = "chrona/presentation-settings/v0.2"
PRESET_VERSION = "chrona/presentation-preset/v0.2"


def _schema(name: str) -> dict[str, Any]:
    return json.loads((_SCHEMA_DIR / f"{name}-v0.2.schema.json").read_text(encoding="utf-8"))


def _validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    settings_schema, preset_schema = _schema("presentation-settings"), _schema("presentation-preset")
    registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in (settings_schema, preset_schema))
    return Draft202012Validator(settings_schema, registry=registry), Draft202012Validator(preset_schema, registry=registry)


def _validate(validator: Draft202012Validator, value: Any, diagnostic: str) -> None:
    if next(validator.iter_errors(value), None) is not None:
        raise PresentationSettingsError(diagnostic)


def _merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Merge objects by key; arrays replace, and null is never a deletion syntax."""
    result = deepcopy(dict(base))
    for key, value in override.items():
        if value is None:
            raise PresentationSettingsError("E_PRESENTATION_PRESET_OVERRIDE")
        result[key] = _merge(result[key], value) if isinstance(value, Mapping) and isinstance(result.get(key), Mapping) else deepcopy(value)
    return result


def _validate_shared_axis_slots(settings: Mapping[str, Any]) -> None:
    """Timeline and axis slots are one temporal scale, never independently windowed."""
    slots = settings["layout"]["slots"]
    timeline = [slot for slot in slots.values() if slot["source"] == "timeline"]
    axis = [slot for slot in slots.values() if slot["source"] == "timeline-axis"]
    if axis and (len(timeline) != 1 or len(axis) != 1):
        raise PresentationSettingsError("E_PRESENTATION_SCALE_MISMATCH")
    if axis and (not timeline[0].get("scaleId") or timeline[0].get("scaleId") != axis[0].get("scaleId")):
        raise PresentationSettingsError("E_PRESENTATION_SCALE_MISMATCH")


def builtin_bases() -> dict[str, dict[str, Any]]:
    return {"executive-v0.2": json.loads(_FIXTURE.read_text(encoding="utf-8"))}


def builtin_base_references() -> dict[str, dict[str, Any]]:
    """Return immutable base declarations, including the exact fixture bytes identity."""
    payload = _FIXTURE.read_bytes()
    return {"executive-v0.2": {"settings": json.loads(payload), "revision": "design-fixture", "contentIdentity": "sha256:" + sha256(payload).hexdigest()}}


def resolve_presentation_settings(resource: Mapping[str, Any], *, bases: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Return complete settings; renderers never receive an unresolved preset."""
    settings_validator, preset_validator = _validators()
    value = deepcopy(dict(resource))
    if value.get("version") == SETTINGS_VERSION:
        _validate(settings_validator, value, "E_PRESENTATION_SETTINGS_REQUIRED")
        _validate_shared_axis_slots(value)
        return value
    if value.get("version") != PRESET_VERSION:
        raise PresentationSettingsError("E_PRESENTATION_SETTINGS_REQUIRED")
    _validate(preset_validator, value, "E_PRESENTATION_PRESET_SCHEMA")
    if "settings" in value:
        _validate(settings_validator, value["settings"], "E_PRESENTATION_SETTINGS_REQUIRED")
        _validate_shared_axis_slots(value["settings"])
        return deepcopy(value["settings"])
    base = (builtin_base_references() if bases is None else bases).get(value["base"]["id"])
    if not isinstance(base, Mapping):
        raise PresentationSettingsError("E_PRESENTATION_REFERENCE")
    reference = value["base"]
    if base.get("revision") != reference["revision"] or base.get("contentIdentity") != reference["contentIdentity"]:
        raise PresentationSettingsError("E_PRESENTATION_REFERENCE")
    base_settings = base.get("settings")
    if not isinstance(base_settings, Mapping) or base_settings.get("version") != SETTINGS_VERSION:
        raise PresentationSettingsError("E_PRESENTATION_REFERENCE")
    _validate(settings_validator, base_settings, "E_PRESENTATION_REFERENCE")
    resolved = _merge(base_settings, value["overrides"])
    _validate(settings_validator, resolved, "E_PRESENTATION_SETTINGS_REQUIRED")
    _validate_shared_axis_slots(resolved)
    return resolved
