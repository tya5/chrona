"""Native outside:omit proof across automatic and fixed-lane geometry."""
from datetime import date

import pytest

from tests.support import synthetic_review as sr


def _source():
    return sr.project({
        "before": sr.span("before", date(2026, 3, 1), 4),
        "after": sr.span("after", date(2026, 3, 24), 4),
    })


def _parts(*, lanes):
    parts = sr.bundle()
    if lanes:
        parts["view"] = sr.lane_view(parts["view"], packing=("explicit",))
    else:
        body = parts["view"]["body"]
        body["rows"] = {"mode": "automatic"}
        body["tableColumns"] = [{"id": "Task", "source": "title", "missing": "em-dash",
                                 "align": "start", "width": "content",
                                 "headerOrientation": "horizontal"}]
        body["visibility"]["labels"]["placement"] = "table"
    parts["view"]["body"]["window"] = {
        "mode": "explicit", "start": "2026-03-10", "end": "2026-03-20",
        "outside": "omit",
    }
    return parts


@pytest.mark.parametrize("lanes", [False, True], ids=["automatic", "fixed-lanes"])
def test_all_outside_rows_are_omitted_but_original_sources_are_accounted(tmp_path, lanes):
    source = _source()
    rendered = sr.render(tmp_path, source, presentation=_parts(lanes=lanes))

    assert rendered.surface.rows == ()
    assert not any(primitive.source_ref in source["objects"]
                   for primitive in rendered.surface.primitives
                   if primitive.slot_id in {"table", "timeline"})
    if lanes:
        assert {(member.row_id, member.member_id) for member in rendered.surface.lane_members} == {
            ('review-lane:["generated","a","before"]', "before"),
            ('review-lane:["generated","a","after"]', "after"),
        }
        assert all(not member.primary_mark_ids and not member.emitted_primitive_ids
                   and member.row_absence is not None
                   and member.row_absence.reason == "outside-window"
                   and member.window_absences
                   for member in rendered.surface.lane_members)
