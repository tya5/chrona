"""A View table column declares per-state affixes that the cell is measured and drawn with (#588).

A small synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from chrona.presentation.model.closure import ClosureError
from tests.support import synthetic_review as sr

START = date(2026, 3, 2)
DELTAS = {"a0": 4, "b0": 0, "c0": -3}      # slip, on time, ahead; d0 has no actual finish


def _source() -> dict:
    objects = {}
    for index, key in enumerate(("a0", "b0", "c0", "d0")):
        objects[key] = sr.span(key, START + timedelta(days=index * 3), 20, owner="a", title=f"Task {key}")
    return sr.project(objects)


def _actual() -> dict:
    observations = []
    for index, key in enumerate(("a0", "b0", "c0")):
        planned_start = START + timedelta(days=index * 3)
        planned_end = planned_start + timedelta(days=20)
        observations.append({"id": f"{key}-observed", "sequence": 1, "projectObjectId": key,
                             "actual": {"start": planned_start.isoformat(),
                                        "finish": (planned_end + timedelta(days=DELTAS[key])).isoformat(), "progress": 1.0}})
    return {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "synthetic-observed",
            "body": {"asOf": (START + timedelta(days=60)).isoformat(), "observations": observations}}


def _presentation(affixes=None, *, fmt="signedNumber", missing="blank", width="content") -> dict:
    parts = sr.bundle("executive-light")
    column = {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": fmt, "missing": missing,
              "align": "end", "width": width, "headerOrientation": "horizontal"}
    if affixes is not None:
        column["affixes"] = affixes
    title = {"id": "Task", "source": "title", "missing": "em-dash", "align": "start", "width": "content",
             "headerOrientation": "horizontal"}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [title, column]
    return parts


def _render(tmp_path: Path, **kwargs):
    return sr.render(tmp_path, _source(), presentation=_presentation(**kwargs), actual=_actual())


def _cells(review) -> dict[str, str]:
    return {item.source_ref: item.text for item in review.surface.primitives
            if item.kind == "Text" and item.purpose == "table-cell" and item.table_column_id == "Delta"}


def _width(review) -> float:
    return next(column.bounds[2] for column in review.surface.columns if column.column_id == "Delta")


AFFIXES = {"slip": {"suffix": "!"}, "missing": {"suffix": "?"}}


def test_each_state_is_drawn_with_its_own_affix_and_an_undeclared_state_is_unchanged(tmp_path) -> None:
    cells = _cells(_render(tmp_path, affixes=AFFIXES))

    assert cells == {"a0": "+4!", "b0": "+0", "c0": "-3", "d0": "?"}


def test_prefix_and_suffix_on_every_state(tmp_path) -> None:
    affixes = {"slip": {"prefix": "(", "suffix": ")!"}, "onTime": {"suffix": " ok"}, "ahead": {"prefix": "<"},
               "missing": {"prefix": "~"}}
    cells = _cells(_render(tmp_path, affixes=affixes))

    assert cells == {"a0": "(+4)!", "b0": "+0 ok", "c0": "<-3", "d0": "~"}


def test_signed_days_keeps_its_unit_and_the_missing_text_is_wrapped_too(tmp_path) -> None:
    cells = _cells(_render(tmp_path, affixes=AFFIXES, fmt="signedDays", missing="em-dash"))

    assert cells == {"a0": "+4d!", "b0": "+0d", "c0": "-3d", "d0": "—?"}


def test_a_view_without_affixes_draws_the_formatted_text(tmp_path) -> None:
    review = _render(tmp_path)

    assert _cells(review) == {"a0": "+4", "b0": "+0", "c0": "-3", "d0": ""}


def test_a_content_column_is_exactly_as_wide_as_with_the_affixes_typed_into_the_values(tmp_path) -> None:
    (tmp_path / "plain").mkdir()
    (tmp_path / "wide").mkdir()
    plain = _render(tmp_path / "plain")
    affixed = _render(tmp_path, affixes={"slip": {"suffix": "!!!!!!"}})
    wide = _render(tmp_path / "wide", affixes={"slip": {"suffix": "!!!!!!"}})

    assert _width(affixed) > _width(plain)
    assert _width(affixed) == _width(wide)
    assert _cells(affixed)["a0"] == "+4!!!!!!"


def _narrow(tmp_path, inline: int):
    parts = _presentation(affixes={"slip": {"suffix": "!!"}}, fmt="signedDays", width="fill")
    sr.fix_inline(parts, "table", inline)
    sr.find_node(parts["layout"], "table")["overflow"] = "ellipsize-with-source"
    return sr.render(tmp_path, _source(), presentation=parts, actual=_actual())


def test_a_narrow_column_ellipsizes_the_value_and_keeps_the_affix(tmp_path) -> None:
    cells = _cells(_narrow(tmp_path, 120))

    assert cells["a0"] == "+…!!"          # the core is cut, the state's affix survives
    assert cells["b0"] == "+0d" and cells["c0"] == "-3d"


def test_when_the_affix_alone_does_not_fit_the_whole_string_is_ellipsized(tmp_path) -> None:
    cells = _cells(_narrow(tmp_path, 80))

    assert cells["a0"] != "!!" and "!" not in cells["a0"][:-1]


@pytest.mark.parametrize(("affixes", "fmt", "code"), [
    ({"late": {"suffix": "!"}}, "signedNumber", "E_VIEW_SCHEMA"),                   # unknown state
    ({"slip": {}}, "signedNumber", "E_VIEW_SCHEMA"),                                 # nothing declared
    ({"slip": {"suffix": "123456789"}}, "signedNumber", "E_VIEW_SCHEMA"),            # over eight characters
    ({"slip": {"suffix": "!", "extra": 1}}, "signedNumber", "E_VIEW_SCHEMA"),
    ({"slip": {"suffix": "\n"}}, "signedNumber", "E_VIEW_COLUMN_AFFIX"),             # control character
    ({"slip": {"suffix": "!"}}, "text", "E_VIEW_COLUMN_AFFIX"),                      # a signed state on a text column
    ({"ahead": {"suffix": "!"}}, "dateRange", "E_VIEW_COLUMN_AFFIX"),
])
def test_a_malformed_or_unusable_affix_is_refused_before_layout(tmp_path, affixes, fmt, code) -> None:
    with pytest.raises(ClosureError) as error:
        _render(tmp_path, affixes=affixes, fmt=fmt)

    assert error.value.diagnostic_id == code


def test_the_missing_affix_alone_is_valid_on_a_text_column(tmp_path) -> None:
    review = _render(tmp_path, affixes={"missing": {"suffix": "?"}}, fmt="text")

    assert _cells(review)["d0"] == "?"
