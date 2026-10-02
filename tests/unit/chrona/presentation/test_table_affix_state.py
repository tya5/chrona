"""The state of a table cell value and the unit-less signed format (#588). Synthetic values only."""
from __future__ import annotations

import pytest

from chrona.presentation.model.surface_content import display_value
from chrona.presentation.table_presentation import CellAffix, ColumnAffixes, affix_state


@pytest.mark.parametrize(("value", "formatter", "state"), [
    (1, "signedDays", "slip"), (0, "signedDays", "onTime"), (-1, "signedDays", "ahead"),
    (1, "signedNumber", "slip"), (0, "signedNumber", "onTime"), (-1, "signedNumber", "ahead"),
    (None, "signedNumber", "missing"), (None, "text", "missing"), (None, "dateRange", "missing"),
    (5, "text", None), (5, "date", None), (True, "signedNumber", None), ("5", "signedNumber", None),
])
def test_the_state_follows_the_value_never_the_text(value, formatter, state) -> None:
    assert affix_state(value, formatter) == state


def test_signed_number_has_a_sign_and_no_unit() -> None:
    assert [display_value(value, "blank", "signedNumber") for value in (10, 0, -3)] == ["+10", "+0", "-3"]
    assert [display_value(value, "blank", "signedDays") for value in (10, 0, -3)] == ["+10d", "+0d", "-3d"]
    assert display_value(None, "blank", "signedNumber") == "" and display_value(None, "em-dash", "signedNumber") == "—"


def test_both_signed_formats_are_set_in_the_numeric_typography_role() -> None:
    from types import SimpleNamespace

    from chrona.presentation.review.v05_content import cell_typography_role

    assert [cell_typography_role(SimpleNamespace(format=name)) for name in ("signedDays", "signedNumber", "text")] == [
        "numeric", "numeric", "text"]


@pytest.mark.parametrize("declared", [
    {"late": {"suffix": "!"}}, {}, {"slip": {}}, {"slip": {"suffix": ""}}, {"slip": {"suffix": "123456789"}},
    {"slip": {"suffix": "!", "extra": "x"}}, {"slip": {"suffix": "\t"}}, {"slip": "!"}, [],
])
def test_the_contract_closes_a_malformed_affix_mapping_itself(declared) -> None:
    from chrona.presentation.contracts.resources import ContractError, _column_affixes

    with pytest.raises(ContractError) as error:
        _column_affixes("Delta", declared)
    assert error.value.diagnostic_id == "E_VIEW_COLUMN_AFFIX" or error.value.code == "E_VIEW_COLUMN_AFFIX"


def test_a_state_without_an_entry_has_no_affix() -> None:
    affixes = ColumnAffixes(slip=CellAffix(suffix="!"), missing=CellAffix(suffix="?"))

    assert affixes.for_state("slip") == CellAffix("", "!") and affixes.for_state("missing") == CellAffix("", "?")
    assert affixes.for_state("onTime") is None and affixes.for_state("ahead") is None
    assert affixes.for_state(None) is None and affixes.for_state("unknown") is None
