"""Ingress-only resolution for the deliberately finite derived Theme form."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any
import jsonschema
from chrona.core.identity import content_identity
from chrona.resources import safe_load, schema_document

class ThemeInheritanceError(ValueError):
    def __init__(self, code: str):
        super().__init__(code); self.code = code

def _child(parent: Path, address: object) -> Path:
    if not isinstance(address, str): raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH")
    path = PurePosixPath(address)
    if not address or path.is_absolute() or address != path.as_posix() or any(item in {"", ".", ".."} for item in path.parts):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_PATH")
    return parent.joinpath(*path.parts)

def resolve_draft_theme(path: Path, stack: tuple[Path, ...] = ()) -> dict[str, Any]:
    """Return a complete v0.11 Theme, never an inheritance source document."""
    resolved_path = path.resolve()
    if resolved_path in stack: raise ThemeInheritanceError("E_THEME_INHERITANCE_CYCLE")
    try: value = safe_load(path.read_bytes())
    except OSError as error: raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_MISSING") from error
    if not isinstance(value, dict): raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA")
    if value.get("version") == "chrona/theme/v0.11": return value
    if value.get("version") != "chrona/theme/v0.12" or value.get("kind") != "theme": return value
    if tuple(jsonschema.Draft202012Validator(schema_document("theme-v0.12.schema.yaml")).iter_errors(value)):
        raise ThemeInheritanceError("E_THEME_INHERITANCE_SCHEMA")
    reference = value["body"]["extends"]
    base = resolve_draft_theme(_child(path.parent, reference["path"]), stack + (resolved_path,))
    if base.get("kind") != "theme" or base.get("version") != "chrona/theme/v0.11" or base.get("id") != reference["id"]:
        raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_KIND")
    if content_identity(base) != reference["contentIdentity"]: raise ThemeInheritanceError("E_THEME_INHERITANCE_BASE_IDENTITY")
    effective = deepcopy(base); effective["id"] = value["id"]
    for name in ("values", "roles"):
        replacement, target = value["body"].get(name, {}), effective["body"][name]
        if any(key not in target for key in replacement): raise ThemeInheritanceError("E_THEME_INHERITANCE_OVERRIDE_UNKNOWN")
        target.update(deepcopy(replacement))
    return effective
