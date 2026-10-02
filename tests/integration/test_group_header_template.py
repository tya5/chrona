"""#583 I583-1: a View-declared group-header text template, rendered end to end.

A Project built in `tests/support/synthetic_review.py` goes through the packaged `control-room-dark`
bundle (which groups by `owner` with header presentation). No `examples/` input.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.support import synthetic_review as sr

OWNERS = ("bus", "payload", "ground")


def _project(secondary: bool = True, owners: tuple[str, ...] = OWNERS):
    objects = {f"t-{owner}": sr.span(f"t-{owner}", date(2026, 1, 5) + timedelta(days=index * 3), 14, owner=owner)
               for index, owner in enumerate(owners)}
    source = sr.project(objects)
    for owner in owners:
        source["entities"][owner]["title"] = owner.title()
        if secondary:
            source["entities"][owner]["fields"] = {"titleJa": f"{owner}-ja"}
    return source


def _render(tmp_path, header=None, *, source=None, grouping=None):
    parts = sr.bundle("control-room-dark")
    if grouping is not None:
        parts["view"]["body"]["grouping"] = grouping
    if header is not None:
        parts["view"]["body"]["grouping"]["header"] = header
    return sr.render(tmp_path, source or _project(), presentation=parts)


def _headers(rendered):
    return {item.scene_id.removeprefix("group-header:"): item.text
            for item in rendered.surface.primitives if item.scene_id.startswith("group-header:")}


def test_without_a_header_template_the_header_is_the_entity_title(tmp_path):
    assert _headers(_render(tmp_path)) == {"bus": "Bus", "payload": "Payload", "ground": "Ground"}


@pytest.mark.parametrize("form,expected", [
    ("arabic", ["ACT 1 · Bus", "ACT 2 · Payload", "ACT 3 · Ground"]),
    ("zero-padded", ["ACT 01 · Bus", "ACT 02 · Payload", "ACT 03 · Ground"]),
    ("roman", ["ACT I · Bus", "ACT II · Payload", "ACT III · Ground"]),
])
def test_each_ordinal_form_numbers_the_groups_in_display_order(tmp_path, form, expected):
    rendered = _render(tmp_path, {"text": "ACT {ordinal} · {title}", "ordinal": form})
    texts = _headers(rendered)
    order = [item.scene_id.removeprefix("group-header:") for item in rendered.surface.primitives
             if item.scene_id.startswith("group-header:")]
    assert [texts[group] for group in order] == expected


def test_the_first_group_may_be_phrased_differently(tmp_path):
    rendered = _render(tmp_path, {"text": "Meanwhile, in the {title}", "first": "In the {title}"})
    texts = _headers(rendered)
    assert list(texts.values()) == ["In the Bus", "Meanwhile, in the Payload", "Meanwhile, in the Ground"]


def test_a_secondary_title_comes_from_the_entity_field(tmp_path):
    rendered = _render(tmp_path, {"text": "{ordinal} {title} {secondary}", "ordinal": "zero-padded",
                                  "secondary": {"entityField": "titleJa"}})
    assert list(_headers(rendered).values()) == ["01 Bus bus-ja", "02 Payload payload-ja", "03 Ground ground-ja"]


def test_braces_can_be_literal(tmp_path):
    rendered = _render(tmp_path, {"text": "{{{title}}}"})
    assert list(_headers(rendered).values()) == ["{Bus}", "{Payload}", "{Ground}"]


def test_a_missing_secondary_value_names_the_group_and_field(tmp_path):
    source = _project()
    del source["entities"]["payload"]["fields"]
    with pytest.raises(ValueError) as failure:
        _render(tmp_path, {"text": "{title} {secondary}", "secondary": {"entityField": "titleJa"}}, source=source)
    assert "E_REVIEW_GROUP_HEADER_SECONDARY" in str(failure.value) and "payload" in str(failure.value)


def test_an_ordinal_past_the_range_of_its_form_is_an_error_not_a_fallback(tmp_path):
    owners = tuple(f"g{index:03d}" for index in range(100))
    # 100 groups exceed the kanji range (1 to 99); only the form in use is checked.
    with pytest.raises(ValueError) as failure:
        _render(tmp_path, {"text": "{ordinal} {title}", "ordinal": "kanji"}, source=_project(owners=owners))
    assert "E_REVIEW_GROUP_ORDINAL_RANGE" in str(failure.value)


def test_a_template_without_an_ordinal_placeholder_does_not_check_the_ordinal_range(tmp_path):
    owners = tuple(f"g{index:03d}" for index in range(100))
    rendered = _render(tmp_path, {"text": "{title}", "ordinal": "kanji"}, source=_project(owners=owners))
    assert len(_headers(rendered)) == 100


def test_a_header_template_on_a_band_grouping_is_rejected_at_the_contract(tmp_path):
    parts_grouping = {"by": "field", "field": "owner", "missing": "Other", "presentation": "band"}
    with pytest.raises(Exception) as failure:
        _render(tmp_path, {"text": "{title}"}, grouping=parts_grouping)
    assert "E_VIEW_GROUP_HEADER_UNUSABLE" in str(failure.value)


def test_a_secondary_declaration_nothing_uses_is_rejected_at_the_contract(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, {"text": "{title}", "secondary": {"entityField": "titleJa"}})
    assert "E_VIEW_GROUP_HEADER_TEMPLATE" in str(failure.value)


def test_an_unknown_placeholder_is_rejected_at_the_contract(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, {"text": "{owner}"})
    assert "E_VIEW_GROUP_HEADER_TEMPLATE" in str(failure.value)
