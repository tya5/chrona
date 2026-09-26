from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator
import pytest

from chrona.resources import axis_name_tables_resource, safe_load, schema_document
from chrona.presentation.model.axis_names import axis_name_catalog, axis_name_table, validate_axis_name_catalog


def _document():
    return safe_load(axis_name_tables_resource().read_bytes())


def test_packaged_catalog_matches_schema_and_declares_every_coincidence():
    document = _document()
    Draft202012Validator(schema_document("axis-name-tables-v0.1.schema.yaml")).validate(document)
    catalog = validate_axis_name_catalog(document)
    assert set(catalog) == {"en-US", "ja-JP"}
    assert [(item.alias, item.canonical, item.months) for item in catalog["en-US"].coincidences] == [
        ("long-month", "short-month", (5,)),
        ("long-month-year", "short-month-year", (5,)),
    ]
    assert catalog["ja-JP"].coincident_canonicals("long-month", 1) == ("short-month",)
    assert axis_name_catalog()["en-US"].table_id == "en-US"
    with pytest.raises(TypeError):
        catalog["en-US"].templates["short-month"] = "tampered"


@pytest.mark.parametrize("mutation", [
    lambda value: value["tables"]["en-US"]["coincidences"].clear(),
    lambda value: value["tables"]["en-US"]["coincidences"][0]["months"].append(6),
    lambda value: value["tables"]["ja-JP"]["monthShort"].pop(),
    lambda value: value["tables"]["en-US"]["templates"].update({"short-month": "{monthShort.__class__}"}),
    lambda value: value["tables"]["en-US"]["templates"].update({"short-month": "{monthShort:>8}"}),
])
def test_invalid_or_undeclared_catalog_data_is_rejected(mutation):
    document = deepcopy(_document())
    mutation(document)
    with pytest.raises(ValueError, match="E_AXIS_NAME_TABLE_RESOURCE"):
        validate_axis_name_catalog(document)


def test_unknown_table_does_not_fall_back_to_locale_or_host():
    with pytest.raises(ValueError, match="E_AXIS_NAME_TABLE_UNKNOWN"):
        axis_name_table("fr-FR")
