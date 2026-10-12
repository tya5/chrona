"""Count text declarations are shared, immutable and independent of values (#1346)."""
from dataclasses import FrozenInstanceError

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import ContractError, SchemaContractError
from chrona.presentation.contracts.view_defaults import merge_view_defaults
from chrona.presentation.count_text import CountTextFormat
from chrona.resources import schema_validator
from tests.support import synthetic_review as sr


def _view(formats, *, figures=None):
    value = sr.bundle("control-room-dark")["view"]
    value["body"]["figures"] = figures if figures is not None else [
        {"id": "n", "kind": "count", "source": "selected"}]
    value["body"]["figureFormats"] = formats
    return parse_contract(ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value).view


@pytest.mark.parametrize("declaration,expected", [
    ({"form": "digits"}, CountTextFormat()),
    ({"form": "digits", "minimumDigits": 3}, CountTextFormat("digits", 3)),
    ({"form": "english-words"}, CountTextFormat("english-words")),
    ({"form": "english-words", "capitalize": True}, CountTextFormat("english-words", capitalize=True)),
    ({"form": "kanji"}, CountTextFormat("kanji")),
    ({"form": "kanji-formal"}, CountTextFormat("kanji-formal")),
])
def test_count_formats_are_typed_without_reading_count_values(declaration, expected):
    view = _view({"n": declaration})
    assert view.figure_formats == {"n": expected}
    layout = sr.bundle("control-room-dark")["layout"]
    layout["viewDefaults"] = {"figureFormats": {"n": declaration}}
    schema_validator("layout-profile-v0.10.schema.yaml").validate(layout)
    with pytest.raises(TypeError):
        view.figure_formats["n"] = CountTextFormat()
    with pytest.raises(FrozenInstanceError):
        view.figure_formats["n"].form = "digits"


@pytest.mark.parametrize("declaration", [
    {}, {"form": "unknown"}, {"form": "digits", "minimumDigits": 0},
    {"form": "digits", "minimumDigits": 81}, {"form": "digits", "minimumDigits": True},
    {"form": "digits", "capitalize": False}, {"form": "kanji", "minimumDigits": 1},
    {"form": "kanji", "capitalize": False}, {"form": "english-words", "capitalize": 1},
    {"form": "english-words", "minimumDigits": 1}, {"form": "digits", "extra": 1},
])
def test_format_shape_options_are_schema_errors_in_both_resources(declaration):
    with pytest.raises(SchemaContractError) as caught:
        _view({"n": declaration})
    assert caught.value.source_ref.startswith("/body/figureFormats/n")
    layout = sr.bundle("control-room-dark")["layout"]
    layout["viewDefaults"] = {"figureFormats": {"n": declaration}}
    assert list(schema_validator("layout-profile-v0.10.schema.yaml").iter_errors(layout))


@pytest.mark.parametrize("identifier,figures", [
    ("absent", []),
    ("a/b~c", []),
    ("days", [{"id": "days", "kind": "daysUntil", "to": "asOf"}]),
])
def test_format_targets_must_name_count_figures_with_exact_escaped_pointer(identifier, figures):
    with pytest.raises(ContractError) as caught:
        _view({identifier: {"form": "digits"}}, figures=figures)
    error = caught.value
    assert error.diagnostic_id == "E_VIEW_FIGURE_FORMAT_INVALID"
    assert error.source_ref == "/body/figureFormats/" + identifier.replace("~", "~0").replace("/", "~1")


@pytest.mark.parametrize("source", ["groups", "placedNotes"])
def test_new_count_sources_are_global_only(source):
    declaration = {"id": "n", "kind": "count", "source": source, "scope": "group"}
    with pytest.raises(ContractError) as caught:
        _view({}, figures=[declaration])
    assert caught.value.diagnostic_id == "E_VIEW_FIGURE_INVALID"
    assert caught.value.source_ref == "/body/figures/0/scope"


def test_format_defaults_replace_as_a_whole_including_empty_map_without_mutation():
    defaults = {"figureFormats": {"n": {"form": "english-words"}}}
    assert merge_view_defaults({"body": {}}, defaults)["body"]["figureFormats"] == defaults["figureFormats"]
    assert merge_view_defaults({"body": {"figureFormats": {}}}, defaults)["body"]["figureFormats"] == {}
    own = {"m": {"form": "digits", "minimumDigits": 2}}
    merged = merge_view_defaults({"body": {"figureFormats": own}}, defaults)
    assert merged["body"]["figureFormats"] == own
    merged["body"]["figureFormats"]["m"]["minimumDigits"] = 3
    assert own["m"]["minimumDigits"] == 2
    assert defaults == {"figureFormats": {"n": {"form": "english-words"}}}


def test_live_view_and_layout_use_the_same_frozen_format_definition():
    view = schema_validator("view-v0.28.schema.yaml").schema
    layout = schema_validator("layout-profile-v0.10.schema.yaml").schema
    body = view["allOf"][1]["properties"]["body"]
    assert body["properties"]["figureFormats"]["$ref"] == layout["properties"]["viewDefaults"]["properties"]["figureFormats"]["$ref"]
