import pytest

from chrona.presentation.contracts import ClosureIdentity, SchemaContractError, parse_contract


def _view_with_width(width):
    return {
        "version": "chrona/view/v0.28",
        "kind": "view",
        "id": "synthetic-hierarchy-width",
        "body": {
            "surface": "table-timeline",
            "selection": {"include": {"types": ["span", "point"]}},
            "grouping": {"by": "hierarchy", "depth": 1, "rollup": "header", "presentation": "header"},
            "ordering": {"by": "id", "direction": "ascending", "tieBreak": "id"},
            "window": {"mode": "selected-planned"},
            "comparison": {
                "baseline": "primary", "actual": "optional", "observationSelection": "latest",
                "deltaUnit": "calendar-days", "facets": [],
            },
            "visibility": {"labels": False, "relations": "none", "annotations": "none"},
            "rows": {"mode": "automatic"},
            "hierarchyColumn": "title",
            "tableColumns": [{
                "id": "title", "source": "title", "missing": "em-dash", "align": "start",
                "width": width, "headerOrientation": "horizontal",
            }],
        },
    }


def _parse_width(width):
    value = _view_with_width(width)
    return parse_contract(ClosureIdentity("view", value["id"], "r", "sha256:" + "a" * 64), value)


@pytest.mark.parametrize("width", (
    "content",
    "fill",
    {"fr": 0.001},
    {"fr": 1_000_000},
    {"minmax": {"min": "content", "max": "content"}},
    {"minmax": {"min": "content", "max": "fill"}},
    {"minmax": {"min": "content", "max": {"fr": 1}}},
))
def test_view_column_accepts_exact_table_width_grammar(width):
    assert _parse_width(width).view.table_columns[0].width is not None


@pytest.mark.parametrize("width", (
    {"fixed": 96},
    "min-content",
    "max-content",
    {"fitContent": 96},
    {"aspectRatio": 1},
    {"fr": 0},
    {"fr": -1},
    {"fr": True},
    {"fr": "1"},
    {"fr": 1_000_000.01},
    {"minmax": {"min": "content"}},
    {"minmax": {"min": "fill", "max": "fill"}},
    {"minmax": {"min": "content", "max": "fill", "extra": 1}},
    {"minmax": {"min": "content", "max": {"fr": 1, "extra": 1}}},
    {"fr": 1, "extra": 1},
))
def test_view_column_rejects_widths_outside_exact_table_grammar(width):
    with pytest.raises(SchemaContractError, match="E_RESOURCE_SCHEMA") as error:
        _parse_width(width)
    assert error.value.violation is not None
    assert error.value.violation.pointer == "/body/tableColumns/0/width"
