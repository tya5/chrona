"""The one-page card (docs/guides/terse-plan.md) must teach plans that compile and schedule (#148)."""
from __future__ import annotations

from pathlib import Path

from chrona.scheduling.scheduler import schedule
from tools.check_documented_commands import discover_plans
from tests.support.terse_plans import compile_text

ROOT = Path(__file__).resolve().parents[4]
CARD = Path("docs/guides/terse-plan.md")


def test_every_plan_on_the_card_compiles_validates_and_schedules():
    plans = [plan for plan in discover_plans(ROOT) if plan.path == CARD]
    assert len(plans) >= 2
    for plan in plans:
        compiled = compile_text(plan.text)
        assert compiled.ok, [item.as_dict() for item in compiled.diagnostics]
        result = schedule(compiled.project)
        assert result.ok, [(item.id, item.path) for item in result.diagnostics]


def test_the_card_stays_one_page_and_names_the_loop():
    text = (ROOT / CARD).read_text(encoding="utf-8")
    assert len(text.splitlines()) <= 120
    for needle in ("chrona compile", "chrona validate", "chrona schedule", "chrona render", "sourceRange", "exclusive", "from DATE"):
        assert needle in text


# The statements the card makes about gates, calendars and lags are facts about the compiler and the scheduler.

def _placements(text: str) -> dict:
    compiled = compile_text(text)
    assert compiled.ok, [item.as_dict() for item in compiled.diagnostics]
    result = schedule(compiled.project)
    assert result.ok, [(item.id, item.path) for item in result.diagnostics]
    return {name: {key: value.isoformat() for key, value in placement.items()} for name, placement in result.placements.items()}


_CALENDARS = 'project p "P" calendar std\ncalendar std mon-fri\ncalendar six mon-sat\n'


def test_a_gate_with_a_date_and_after_is_a_floor_and_the_scheduler_rejects_a_later_dependency():
    base = 'project p "P"\na "A" task 2027-03-01..{end}\ng "G" gate {date} after a +2d\n'
    assert _placements(base.format(end="2027-03-08", date="2027-03-10"))["g"] == {"at": "2027-03-10"}  # the card's example
    assert _placements(base.format(end="2027-03-08", date="2027-03-20"))["g"] == {"at": "2027-03-20"}  # it sits on its date
    late = compile_text(base.format(end="2027-03-12", date="2027-03-10"))
    assert late.ok
    rejected = schedule(late.project)
    assert not rejected.ok and [item.id for item in rejected.diagnostics] == ["E_FIXED_TARGET_VIOLATION"]


def test_a_gate_cannot_be_derived_from_its_dependencies():
    compiled = compile_text('project p "P"\na "A" task 2027-03-01..2027-03-08\ng "G" gate after a +2d\n')
    assert [item.id for item in compiled.diagnostics] == ["E_TERSE_SCHEDULE_REQUIRED"]


def test_an_objects_calendar_overrides_the_project_default():
    placed = _placements(_CALENDARS + 'b "B" task 5wd from 2027-03-01 calendar six\nc "C" task 5wd from 2027-03-01\n')
    assert placed["b"]["end"] == "2027-03-06"  # Mon-Sat calendar
    assert placed["c"]["end"] == "2027-03-08"  # Mon-Fri, the project default


def test_a_wd_lag_without_in_is_counted_on_the_calendar_of_the_object_carrying_the_after():
    text = (_CALENDARS + 'a "A" task 1d from 2027-03-04\n'
            'plain-std "x" task 2wd after a +3wd\nplain-six "x" task 2wd calendar six after a +3wd\n'
            'six-in-std "x" task 2wd calendar six after a +3wd in std\nstd-in-six "x" task 2wd after a +3wd in six\n')
    starts = {name: place["start"] for name, place in _placements(text).items()}
    assert starts["plain-six"] == starts["std-in-six"] != starts["plain-std"] == starts["six-in-std"]
    other = _placements(text.replace('a "A" task 1d from 2027-03-04', 'a "A" task 1d from 2027-03-04 calendar six'))
    assert other["plain-std"]["start"] == starts["plain-std"]  # the predecessor's calendar does not matter


def test_w_is_a_lag_unit_and_a_lag_may_follow_an_endpoint():
    placed = _placements('project p "P"\na "A" task 2026-10-01..2026-10-10\nc "C" task 5d after a\n'
                         'd "D" task 3d after c.start +1w\nw1 "W1" task 3d after a +1w\nw2 "W2" task 3d after a -1w\n')
    assert placed["d"]["start"] == "2026-10-17" and placed["w1"]["start"] == "2026-10-17"
    assert placed["w2"]["start"] == "2026-10-03"
