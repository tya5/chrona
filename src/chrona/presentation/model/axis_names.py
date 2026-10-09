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
    "day-month", "day-month-year",
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


def _invalid(location: str, actual: str, expected: str) -> ValueError:
    return ValueError(f"{_ERROR}: {location}; actual={actual}; expected {expected}")


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
            raise ValueError(f"E_PRESENTATION_AXIS_FORMAT: table={self.table_id!r}, form={form!r}; expected one of {tuple(self.templates)!r}")
        try:
            result = self.templates[form].format_map(components)
        except (KeyError, ValueError) as error:
            raise _invalid(f"table {self.table_id!r} form {form!r}", f"{type(error).__name__} in component/template formatting", "all referenced components present and valid format syntax") from error
        if not result:
            raise _invalid(f"table {self.table_id!r} form {form!r}", "empty formatted result", "nonempty axis label")
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
        raise _invalid(f"tables/{table_id}", f"type={type(raw).__name__}, keys={tuple(raw)[:8] if isinstance(raw, Mapping) else ()!r}", "exact monthShort, monthLong, templates, coincidences fields")
    months = []
    for key in ("monthShort", "monthLong"):
        value = raw[key]
        if not isinstance(value, list) or len(value) != 12 or any(not isinstance(item, str) or not item for item in value):
            bad_index = next((index for index, item in enumerate(value) if not isinstance(item, str) or not item), None) if isinstance(value, list) else None
            raise _invalid(f"tables/{table_id}/{key}", f"type={type(value).__name__}, length={len(value) if isinstance(value, list) else 'n/a'}, invalidIndex={bad_index}", "12 nonempty strings")
        months.append(tuple(value))
    templates, raw_coincidences = raw["templates"], raw["coincidences"]
    if not isinstance(templates, Mapping) or set(templates) != FORMS or not isinstance(raw_coincidences, list):
        raise _invalid(f"tables/{table_id}/templates", f"templatesType={type(templates).__name__}, missingForms={tuple(sorted(FORMS - set(templates))) if isinstance(templates, Mapping) else 'n/a'}, coincidencesType={type(raw_coincidences).__name__}", "all declared forms and a coincidence list")
    for form, template in templates.items():
        if not isinstance(template, str) or not template:
            raise _invalid(f"tables/{table_id}/templates/{form}", f"valueType={type(template).__name__}", "nonempty template string")
        try:
            parsed = tuple(Formatter().parse(template))
        except ValueError as error:
            raise _invalid(f"tables/{table_id}/templates/{form}", "malformed format syntax", "valid format template") from error
        invalid_fields = tuple(field for _, field, spec, conversion in parsed
                               if field is not None and (field not in COMPONENTS or spec or conversion))
        if invalid_fields:
            raise _invalid(f"tables/{table_id}/templates/{form}", f"fields={invalid_fields!r}", f"components only from {tuple(sorted(COMPONENTS))!r}, without format specs or conversions")
    coincidences = []
    for index, item in enumerate(raw_coincidences):
        if (not isinstance(item, Mapping) or set(item) != {"alias", "canonical", "months"}
                or item["alias"] not in MONTH_FORMS or item["canonical"] not in MONTH_FORMS
                or not isinstance(item["months"], list) or not item["months"]
                or any(type(month) is not int or month < 1 or month > 12 for month in item["months"])
                or item["months"] != sorted(set(item["months"]))):
            detail = (f"type={type(item).__name__}" if not isinstance(item, Mapping) else
                      f"alias={item.get('alias')!r}, canonical={item.get('canonical')!r}, monthsType={type(item.get('months')).__name__}")
            raise _invalid(f"tables/{table_id}/coincidences/{index}", detail,
                           "month-form alias/canonical and sorted unique month numbers 1..12")
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
        unexpected = tuple((item.alias, item.canonical, item.months) for item in coincidences if item not in expected)[:4]
        missing = tuple((item.alias, item.canonical, item.months) for item in sorted(expected - set(coincidences), key=lambda item: (item.alias, item.canonical, item.months)))[:4]
        raise _invalid(f"tables/{table_id}/coincidences", f"unexpected={unexpected!r}, missing={missing!r}", "exact month-form coincidences derived from template output")
    return table


def validate_axis_name_catalog(document: Any) -> Mapping[str, AxisNameTable]:
    """Close every built-in table and all month-form equivalences at once."""
    if (not isinstance(document, Mapping) or set(document) != {"version", "tables"}
            or document["version"] != CATALOG_VERSION or not isinstance(document["tables"], Mapping)
            or set(document["tables"]) != TABLE_IDS):
        actual = (f"type={type(document).__name__}" if not isinstance(document, Mapping) else
                  f"version={document.get('version')!r}, tableIds={tuple(document.get('tables', ()))[:8] if isinstance(document.get('tables'), Mapping) else type(document.get('tables')).__name__!r}")
        raise _invalid("catalog root", actual, f"version={CATALOG_VERSION!r} and exact tables {tuple(sorted(TABLE_IDS))!r}")
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
        raise ValueError(f"E_AXIS_NAME_TABLE_UNKNOWN: tableId={table_id!r}; expected one of {tuple(sorted(axis_name_catalog()))!r}") from error
