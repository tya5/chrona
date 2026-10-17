"""Load the wheel-owned semantic vocabulary as immutable presentation data."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from importlib.resources import files
from typing import Any, Mapping

from chrona.resources import safe_load, schema_validator


VERSION = "chrona/semantic-vocabulary/v0.1"
KIND = "semantic-vocabulary"
RESOURCE_ID = "chrona-core"
_SCHEMA = "semantic-vocabulary-v0.1.schema.yaml"


class SemanticVocabularyError(ValueError):
    """A semantic vocabulary cannot be admitted as a complete value."""

    def __init__(self, diagnostic_id: str, detail: str, source_ref: str = "/") -> None:
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail
        self.source_ref = source_ref


@dataclass(frozen=True)
class SemanticVocabularyBinding:
    """One validated, immutable semantic-to-presentation mapping."""

    semantic_id: str
    primitive_family: str
    purpose: str
    scene_role: str
    theme_role: str
    contrast_class: str | None

    def to_mapping(self) -> dict[str, str | None]:
        return {
            "semanticId": self.semantic_id,
            "primitiveFamily": self.primitive_family,
            "purpose": self.purpose,
            "sceneRole": self.scene_role,
            "themeRole": self.theme_role,
            "contrastClass": self.contrast_class,
        }


@dataclass(frozen=True)
class SemanticVocabulary:
    """An immutable loaded resource whose identity names its original bytes."""

    id: str
    version: str
    content_identity: str
    bindings: tuple[SemanticVocabularyBinding, ...]

    def to_envelope(self) -> dict[str, Any]:
        """Return a fresh plain envelope suitable for a typed contract parser."""
        return {
            "version": self.version,
            "kind": KIND,
            "id": self.id,
            "body": {"bindings": [binding.to_mapping() for binding in self.bindings]},
        }


def _invalid(detail: str, source_ref: str = "/") -> SemanticVocabularyError:
    return SemanticVocabularyError("E_SEMANTIC_VOCABULARY_RESOURCE", detail, source_ref)


def validate_semantic_vocabulary(value: Mapping[str, Any]) -> tuple[SemanticVocabularyBinding, ...]:
    """Validate a decoded vocabulary envelope and return ordered frozen rows.

    This mapping entry point intentionally does not calculate content identity:
    only a caller holding the original resource bytes can do that correctly.
    """
    if not isinstance(value, Mapping):
        raise _invalid("semantic vocabulary must be an object")
    if "version" not in value:
        raise _invalid("version is required", "/version")
    version = value.get("version")
    if version != VERSION:
        found = repr(version)
        raise SemanticVocabularyError(
            "E_RESOURCE_VERSION_UNSUPPORTED",
            f"{KIND} id={value.get('id')!r} declares version {found}; supported: {VERSION}",
            "/version",
        )
    if value.get("kind") != KIND:
        raise _invalid(f"expected kind {KIND!r}", "/kind")
    if value.get("id") != RESOURCE_ID:
        raise _invalid(f"expected id {RESOURCE_ID!r}", "/id")
    errors = tuple(schema_validator(_SCHEMA).iter_errors(value))
    if errors:
        error = min(errors, key=lambda item: (len(item.absolute_path),
                                             tuple(map(str, item.absolute_path)), item.message))
        pointer = "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1")
                                  for part in error.absolute_path)
        raise SemanticVocabularyError("E_RESOURCE_SCHEMA", error.message, pointer)

    rows = value["body"]["bindings"]
    seen: set[str] = set()
    for index, row in enumerate(rows):
        semantic_id = row["semanticId"]
        if semantic_id in seen:
            raise SemanticVocabularyError(
                "E_SEMANTIC_VOCABULARY_DUPLICATE_ID",
                f"duplicate semantic id {semantic_id!r}",
                f"/body/bindings/{index}/semanticId",
            )
        seen.add(semantic_id)

    return tuple(SemanticVocabularyBinding(
        semantic_id=row["semanticId"],
        primitive_family=row["primitiveFamily"],
        purpose=row["purpose"],
        scene_role=row["sceneRole"],
        theme_role=row["themeRole"],
        contrast_class=row["contrastClass"],
    ) for row in rows)


def load_semantic_vocabulary(
    payload: bytes, *, expected_content_identity: str | None = None,
) -> SemanticVocabulary:
    """Decode and validate exact resource bytes, then retain their raw SHA-256."""
    if not isinstance(payload, bytes) or not payload:
        raise _invalid("semantic vocabulary resource bytes are missing")
    identity = "sha256:" + sha256(payload).hexdigest()
    if expected_content_identity is not None and identity != expected_content_identity:
        raise SemanticVocabularyError(
            "E_RESOURCE_IDENTITY_MISMATCH",
            "semantic vocabulary content identity does not match the expected identity",
            "/contentIdentity",
        )
    try:
        value = safe_load(payload)
    except Exception as error:
        raise _invalid(f"semantic vocabulary resource cannot be decoded: {error}") from error
    try:
        bindings = validate_semantic_vocabulary(value)
    except SemanticVocabularyError:
        raise
    except Exception as error:
        raise _invalid(f"semantic vocabulary resource is invalid: {error}") from error
    return SemanticVocabulary(RESOURCE_ID, VERSION, identity, bindings)


@cache
def builtin_semantic_vocabulary() -> SemanticVocabulary:
    """Return the one validated wheel-owned vocabulary, cached immutably."""
    try:
        payload = files("chrona.resources").joinpath("semantic-vocabulary.yaml").read_bytes()
    except (OSError, ModuleNotFoundError) as error:
        raise _invalid(f"packaged semantic-vocabulary.yaml is unavailable: {error}") from error
    return load_semantic_vocabulary(payload)
