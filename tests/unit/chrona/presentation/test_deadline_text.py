"""Caption authoring and the authoritative Core-count handoff (#1397 row3)."""
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.core.deadlines import deadline_statuses
from chrona.presentation.contracts.resources import ContractError, _view_deadlines
from chrona.presentation.count_text import CountTextError, CountTextFormat
from chrona.presentation.deadline_text import compile_deadline_caption
from chrona.presentation.group_header_text import GroupHeaderTextError
from chrona.scheduling.scheduler import schedule
from chrona.usecases.render_review import RenderFailed, _shown_deadlines
from tests.support import synthetic_review as sr


@pytest.mark.parametrize(("form", "expected"), [
    ("digits", "3"), ("english-words", "three"), ("kanji", "三"), ("kanji-formal", "参"),
])
def test_caption_reuses_closed_count_forms_and_author_copy(form, expected):
    program = compile_deadline_caption("{{late}}: {daysLate} 日", CountTextFormat(form))
    assert program.bind(3) == "{late}: " + expected + " 日"


@pytest.mark.parametrize("source", ["{figure:late}", "{daysLate|text}", "{other}", "{daysLate", "}"])
def test_caption_has_no_figure_scope_inline_roles_or_other_placeholders(source):
    with pytest.raises(GroupHeaderTextError) as raised:
        compile_deadline_caption(source)
    assert raised.value.code == "E_VIEW_DEADLINE_CAPTION_TEMPLATE"


def test_normalization_closes_defaults_and_points_invalid_copy_at_its_author():
    assert _view_deadlines(None) is None
    assert _view_deadlines({"show": "all"}).caption is None
    selected = _view_deadlines({"show": "all", "caption": {"template": "{daysLate}"}})
    assert selected.caption.bind(3) == "3"
    with pytest.raises(ContractError) as raised:
        _view_deadlines({"show": "all", "caption": {"template": "{other}"}})
    assert (raised.value.diagnostic_id, raised.value.source_ref) == (
        "E_VIEW_DEADLINE_CAPTION_TEMPLATE", "/body/deadlines/caption/template")


def test_formats_do_not_silently_fallback_and_literal_copy_does_not_read_number_names():
    with pytest.raises(CountTextError) as raised:
        compile_deadline_caption("{daysLate}", CountTextFormat("kanji")).bind(100)
    assert raised.value.code == "E_VIEW_FIGURE_FORMAT_RANGE"
    assert compile_deadline_caption("late", CountTextFormat("kanji")).bind(100) == "late"
    assert compile_deadline_caption("{daysLate}", CountTextFormat("digits", 3)).bind(3) == "003"
    assert compile_deadline_caption("{daysLate}", CountTextFormat("english-words", capitalize=True)).bind(3) == "Three"


def test_projection_passes_core_count_and_only_binds_slipped_deadlines():
    source = sr.project({"late": sr.point("late", date(2026, 1, 8)),
                         "kept": sr.point("kept", date(2026, 1, 5))})
    for item in source["objects"].values():
        item["deadline"] = "2026-01-05"
    selected = _view_deadlines({"show": "all", "caption": {"template": "{daysLate} d late"}})
    statuses = deadline_statuses(source, schedule(source).placements)
    shown = _shown_deadlines(source, statuses, SimpleNamespace(deadlines=selected))
    assert [(item.object_id, item.slipped, item.days_late, item.caption) for item in shown] == [
        ("late", True, 3, "3 d late"), ("kept", False, 0, None)]


def test_projection_reports_format_range_at_caption_not_an_invented_figure():
    source = sr.project({"late": sr.point("late", date(2026, 6, 1))})
    source["objects"]["late"]["deadline"] = "2026-01-01"
    selected = _view_deadlines({"show": "slipped", "caption": {
        "template": "{daysLate}", "format": {"form": "kanji"}}})
    statuses = deadline_statuses(source, schedule(source).placements)
    with pytest.raises(RenderFailed) as raised:
        _shown_deadlines(source, statuses, SimpleNamespace(deadlines=selected))
    assert (raised.value.code, raised.value.source_ref) == (
        "E_VIEW_FIGURE_FORMAT_RANGE", "/body/deadlines/caption/format")
