"""A table column's absent-value text can be an author-chosen literal (#1288).

The Sunday Strip shows `?` for a late work package whose actual is missing and nothing for the other blank cells.
Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

import pytest

from tests.integration.test_missing_by import ACTUAL
from tests.support import synthetic_review as sr

from datetime import date


def _cells(tmp_path, *, missing="em-dash", missing_by=None, affixes=None):
    source = sr.project({
        "done": sr.span("done", date(2026, 2, 2), 14, title="Done"),
        "running": sr.span("running", date(2026, 3, 2), 30, title="Running"),
        "overdue": sr.span("overdue", date(2026, 2, 2), 10, title="Overdue"),
        "later": sr.span("later", date(2026, 5, 4), 10, title="Later")})
    parts = sr.bundle("executive-light")
    column = {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays", "missing": missing,
              "align": "end", "width": "content", "headerOrientation": "horizontal"}
    if missing_by is not None:
        column["missingBy"] = missing_by
    if affixes is not None:
        column["affixes"] = affixes
    title = {"id": "Task", "source": "title", "missing": "em-dash", "align": "start", "width": "content",
             "headerOrientation": "horizontal"}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [title, column]
    review = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL)
    return {item.source_ref: item.text for item in review.surface.primitives
            if item.purpose == "table-cell" and item.table_column_id == "Delta"}


def test_a_literal_for_one_state_shows_only_in_the_cells_of_that_state(tmp_path):
    cells = _cells(tmp_path, missing_by={"inProgress": {"text": "?"}, "dueUnobserved": "blank", "notYetDue": "blank"})

    assert cells == {"done": "+4d", "running": "?", "overdue": "", "later": ""}


def test_a_literal_missing_text_is_the_default_of_every_state_not_named(tmp_path):
    cells = _cells(tmp_path, missing={"text": "n/a"}, missing_by={"dueUnobserved": "blank"})

    assert cells == {"done": "+4d", "running": "n/a", "overdue": "", "later": "n/a"}


def test_the_enum_spellings_are_unchanged(tmp_path):
    cells = _cells(tmp_path, missing_by={"inProgress": "em-dash", "dueUnobserved": "blank", "notYetDue": "blank"})

    assert cells == {"done": "+4d", "running": "—", "overdue": "", "later": ""}


def test_the_missing_affix_still_wraps_every_absent_state_around_the_literal(tmp_path):
    cells = _cells(tmp_path, missing_by={"inProgress": {"text": "?"}, "dueUnobserved": "blank", "notYetDue": "blank"},
                   affixes={"missing": {"suffix": "!"}})

    assert cells["running"] == "?!" and cells["overdue"] == "!" and cells["later"] == "!"


@pytest.mark.parametrize("bad", [{"text": ""}, {"text": "123456789"}, {"text": "a\nb"}, {}, {"text": "?", "more": 1}])
def test_a_literal_must_be_one_to_eight_characters_without_control_characters(tmp_path, bad):
    with pytest.raises(Exception) as caught:
        _cells(tmp_path, missing_by={"inProgress": bad})

    assert "E_" in str(caught.value)
