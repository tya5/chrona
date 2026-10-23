"""Candidate-local group header bounds remain stable for empty groups (#1936)."""
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.surface_base import _group_header_inline_bounds


@pytest.mark.parametrize(("vertical", "expected"), [(False, (24.0, 1136.0)), (True, (130.0, 270.0))])
def test_table_owned_header_keeps_legacy_bounds_for_empty_and_populated_groups(vertical, expected):
    fit_plan = SimpleNamespace(header_inline_start=130.0, header_inline_size=270.0,
                               vertical_tag_plan=vertical)

    assert _group_header_inline_bounds(
        table_bounds=(24.0, 80.0, 320.0, 600.0),
        timeline_bounds=(360.0, 80.0, 800.0, 600.0),
        fit_plan=fit_plan,
        placement="table",
    ) == expected


def test_timeline_owned_header_uses_timeline_bounds_even_when_table_has_fit_plan():
    fit_plan = SimpleNamespace(header_inline_start=130.0, header_inline_size=270.0,
                               vertical_tag_plan=False)

    assert _group_header_inline_bounds(
        table_bounds=(24.0, 80.0, 320.0, 600.0),
        timeline_bounds=(360.0, 80.0, 800.0, 600.0),
        fit_plan=fit_plan,
        placement="timeline",
    ) == (360.0, 800.0)
