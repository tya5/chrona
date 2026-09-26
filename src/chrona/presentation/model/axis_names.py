"""Validated, wheel-owned axis name tables independent of document locale."""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from itertools import combinations
from string import Formatter
from types import MappingProxyType
from typing import Any, Mapping

from chrona.resources import axis_name_tables_resource, safe_load


CATALOG_VERSION = "chrona/axis-name-tables/v0.1"
FORMS = frozenset({
    "year", "half-year", "quarter", "year-quarter", "quarter-year",
    "short-month", "long-month", "numeric-month", "short-month-year",
    "long-month-year", "numeric-year-month", "iso-week", "localized-date",
})
MONTH_FORMS = (
    "short-month", "long-month", "numeric-month", "short-month-year",
    "long-month-year", "numeric-year-month",
)
COMPONENTS = frozenset({
    "year", "fiscalYear", "half", "quarter", "monthShort", "monthLong",
    "monthNumber", "monthNumeric", "day", "dayNumeric", "isoYear", "isoWeek",
})
TABLE_IDS = frozenset({"en-US", "ja-JP"})
_ERROR = "E_AXIS_NAME_TABLE_RESOURCE"


@dataclass(frozen=True)
class AxisNameCoincidence:
    alias: str
    canonical: str
    months: tuple[int, ...]


@dataclass(frozen=True)
class AxisNameTable:
    table_id: str
    month_short: tuple[str, ...]
    month_long: tuple[str, ...]
    templates: Mapping[str, str]
    coincidences: tuple[AxisNameCoincidence, ...]

    def format(self, form: str, components: Mapping[str, Any]) -> str:
        if form not in self.templates:
            raise ValueError("E_PRESENTATION_AXIS_FORMAT")
        try:
            result = self.templates[form].format_map(components)
        except (KeyError, ValueError) as error:
            raise ValueError(_ERROR) from error
        if not result:
            raise ValueError(_ERROR)
        return result

    def coincident_canonicals(self, form: str, month: int) -> tuple[str, ...]:
        return tuple(item.canonical for item in self.coincidences
                     if item.alias == form and month in item.months)


def _month_components(table: AxisNameTable, month: int) -> dict[str, Any]:
    return {
        "year": 2026, "fiscalYear": 2026, "half": 1, "quarter": 1,
        "monthShort": table.month_short[month - 1],
        "monthLong": table.month_long[month - 1],
        "monthNumber": month, "monthNumeric": f"{month:02d}",
        "day": 5, "dayNumeric": "05", "isoYear": 2026, "isoWeek": "01",
    }


def _validate_table(table_id: str, raw: Any) -> AxisNameTable:
    if not isinstance(raw, Mapping) or set(raw) != {"monthShort", "monthLong", "templates", "coincidences"}:
        raise ValueError(_ERROR)
    months = []
    for key in ("monthShort", "monthLong"):
        value = raw[key]
        if not isinstance(value, list) or len(value) != 12 or any(not isinstance(item, str) or not item for item in value):
            raise ValueError(_ERROR)
        months.append(tuple(value))
    templates, raw_coincidences = raw["templates"], raw["coincidences"]
    if not isinstance(templates, Mapping) or set(templates) != FORMS or not isinstance(raw_coincidences, list):
        raise ValueError(_ERROR)
    for template in templates.values():
        if not isinstance(template, str) or not template:
            raise ValueError(_ERROR)
        try:
            parsed = tuple(Formatter().parse(template))
        except ValueError as error:
            raise ValueError(_ERROR) from error
        if any(field not in COMPONENTS or spec or conversion for _, field, spec, conversion in parsed if field is not None):
            raise ValueError(_ERROR)
    coincidences = []
    for item in raw_coincidences:
        if (not isinstance(item, Mapping) or set(item) != {"alias", "canonical", "months"}
                or item["alias"] not in MONTH_FORMS or item["canonical"] not in MONTH_FORMS
                or not isinstance(item["months"], list) or not item["months"]
                or any(type(month) is not int or month < 1 or month > 12 for month in item["months"])
                or item["months"] != sorted(set(item["months"]))):
            raise ValueError(_ERROR)
        coincidences.append(AxisNameCoincidence(item["alias"], item["canonical"], tuple(item["months"])))
    table = AxisNameTable(table_id, months[0], months[1], MappingProxyType(dict(templates)), tuple(coincidences))
    expected: set[AxisNameCoincidence] = set()
    for left, right in combinations(MONTH_FORMS, 2):
        equal_months = tuple(month for month in range(1, 13)
                             if table.format(left, _month_components(table, month)) ==
                             table.format(right, _month_components(table, month)))
        if equal_months:
            expected.add(AxisNameCoincidence(right, left, equal_months))
    if len(coincidences) != len(expected) or set(coincidences) != expected:
        raise ValueError(_ERROR)
    return table


def validate_axis_name_catalog(document: Any) -> Mapping[str, AxisNameTable]:
    """Close every built-in table and all month-form equivalences at once."""
    if (not isinstance(document, Mapping) or set(document) != {"version", "tables"}
            or document["version"] != CATALOG_VERSION or not isinstance(document["tables"], Mapping)
            or set(document["tables"]) != TABLE_IDS):
        raise ValueError(_ERROR)
    return MappingProxyType({table_id: _validate_table(table_id, raw)
                             for table_id, raw in sorted(document["tables"].items())})


@cache
def axis_name_catalog() -> Mapping[str, AxisNameTable]:
    """Read the packaged catalog, never a local or host-locale file."""
    return validate_axis_name_catalog(safe_load(axis_name_tables_resource().read_bytes()))


def axis_name_table(table_id: str) -> AxisNameTable:
    try:
        return axis_name_catalog()[table_id]
    except KeyError as error:
        raise ValueError("E_AXIS_NAME_TABLE_UNKNOWN") from error
