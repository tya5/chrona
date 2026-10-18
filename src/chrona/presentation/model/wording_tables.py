"""Validated, wheel-owned built-in wording tables and the one wording resolver (#1724).

Precedence, lowest to highest: the locale table entry; a literal authored in a preset; the View
``wording.keys`` override; the View ``wording.legend`` / ``wording.summary`` entry. This module
owns levels 1, 3 and 4 for built-in text; level 2 is the caller keeping an authored literal.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from types import MappingProxyType
from typing import Any, Mapping

from chrona.resources import safe_load, wording_tables_resource


CATALOG_VERSION = "chrona/wording-tables/v0.1"
TABLE_IDS = frozenset({"en-US", "ja-JP"})
DEFAULT_LOCALE = "en-US"
_ERROR = "E_WORDING_TABLE_RESOURCE"
_LEGEND_PREFIX = "legend."


def _invalid(location: str, actual: str, expected: str) -> ValueError:
    return ValueError(f"{_ERROR}: {location}; actual={actual}; expected {expected}")


def validate_wording_catalog(document: Any) -> Mapping[str, Mapping[str, str]]:
    """Close the catalog: both locales, the same keys, nonempty text, nothing shared across locales."""
    if (not isinstance(document, Mapping) or set(document) != {"version", "tables"}
            or document["version"] != CATALOG_VERSION or not isinstance(document["tables"], Mapping)
            or set(document["tables"]) != TABLE_IDS):
        raise _invalid("catalog root", f"type={type(document).__name__}",
                       f"version={CATALOG_VERSION!r} and exact tables {tuple(sorted(TABLE_IDS))!r}")
    tables = document["tables"]
    reference = tables[DEFAULT_LOCALE]
    if not isinstance(reference, Mapping) or not reference:
        raise _invalid(f"tables/{DEFAULT_LOCALE}", f"type={type(reference).__name__}", "a nonempty key to text mapping")
    keys = set(reference)
    for table_id, table in sorted(tables.items()):
        if not isinstance(table, Mapping) or set(table) != keys:
            missing = tuple(sorted(keys - set(table))) if isinstance(table, Mapping) else "n/a"
            extra = tuple(sorted(set(table) - keys)) if isinstance(table, Mapping) else "n/a"
            raise _invalid(f"tables/{table_id}", f"missing={missing!r}, extra={extra!r}", "the same wording keys in every locale")
        for key, text in table.items():
            if not isinstance(text, str) or not text.strip():
                raise _invalid(f"tables/{table_id}/{key}", f"valueType={type(text).__name__}", "nonempty text")
    return MappingProxyType({table_id: MappingProxyType(dict(table)) for table_id, table in sorted(tables.items())})


@cache
def wording_catalog() -> Mapping[str, Mapping[str, str]]:
    """Read the packaged catalog, never a local or host-locale file."""
    return validate_wording_catalog(safe_load(wording_tables_resource().read_bytes()))


def wording_keys() -> tuple[str, ...]:
    """Every built-in wording key, in table order."""
    return tuple(wording_catalog()[DEFAULT_LOCALE])


def is_wording_ref(value: Any) -> bool:
    return isinstance(value, Mapping) and set(value) == {"wording"} and isinstance(value["wording"], str)


@dataclass(frozen=True)
class WordingResolver:
    """Resolve built-in wording for one Render Context locale and one View's overrides."""

    locale: str = DEFAULT_LOCALE
    keys: Mapping[str, str] = MappingProxyType({})
    legend: Mapping[str, str] = MappingProxyType({})

    def table_text(self, key: str) -> str:
        """The locale entry (level 1); the en-US entry stands in for an unsupported locale."""
        catalog = wording_catalog()
        table = catalog.get(self.locale, catalog[DEFAULT_LOCALE])
        try:
            return table[key]
        except KeyError as error:
            raise ValueError(f"E_WORDING_KEY_UNKNOWN: key={key!r}; expected one of {wording_keys()!r}") from error

    def text(self, key: str) -> str:
        """A key's text: the View ``wording.keys`` override (level 3) over the table entry."""
        override = self.keys.get(key)
        return str(override) if override is not None else self.table_text(key)

    def legend_text(self, role: str, literal: str | None = None) -> str:
        """A legend role's label: ``wording.legend`` (level 4), ``wording.keys``, an authored literal, the table."""
        if role in self.legend:
            return str(self.legend[role])
        key = _LEGEND_PREFIX + role
        if key in self.keys:
            return str(self.keys[key])
        return literal if literal is not None else self.table_text(key)

    def resolve(self, value: Any) -> str:
        """An authored literal stays as written (level 2); a ``{wording: key}`` reference becomes its text."""
        if is_wording_ref(value):
            return self.text(value["wording"])
        return str(value)

    def missing_words(self) -> Mapping[str, str]:
        """The words for an absent value, by the ``display_value`` missing-spelling."""
        return {"unknown": self.text("missing.unknown"), "in-progress": self.text("missing.inProgress")}


def wording_resolver(locale: str, wording: Mapping[str, Any] | None) -> WordingResolver:
    """The resolver for a Render Context locale and a View's ``wording`` mapping."""
    wording = wording or {}
    return WordingResolver(locale, dict(wording.get("keys", {})), dict(wording.get("legend", {})))
