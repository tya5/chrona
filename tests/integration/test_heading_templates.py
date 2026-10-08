"""A View's `heading` declares the title and subtitle lines (#991), end to end.

A small synthetic Project goes through the packaged `control-room-dark` bundle (its Theme declares the
`heading` and `subtitle` typography roles), so no corpus edit can change what these tests prove.
No test reads `examples/`.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}


def _source() -> dict:
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 20, title="Alpha"), "b": sr.span("b", date(2026, 3, 2), 20, title="Beta")})
    source["project"]["title"] = "HALCYON"
    source["project"]["calendar"] = "engineering"
    source["calendars"] = {"engineering": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    return source


def _render(tmp_path, heading: dict | None, *, theme_edit=None):
    parts = sr.bundle("control-room-dark")
    if heading is not None:
        parts["view"]["body"]["heading"] = deepcopy(heading)
    if theme_edit is not None:
        theme_edit(parts["theme"])
    return sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL)


def _texts(rendered) -> dict[str, object]:
    return {item.scene_id: item for item in rendered.surface.primitives if item.scene_id in {"title", "subtitle"}}


def test_without_a_heading_the_title_is_the_project_title_and_there_is_no_subtitle(tmp_path):
    texts = _texts(_render(tmp_path, None))
    assert texts["title"].text == "HALCYON"
    assert "subtitle" not in texts


def test_a_declared_heading_composes_both_lines_from_project_facts(tmp_path):
    rendered = _render(tmp_path, {"title": "{project} · Programme board",
                                  "subtitle": "as of {asOf} · calendar: {calendar} {{kept}}"})
    texts = _texts(rendered)

    assert texts["title"].text == "HALCYON · Programme board"
    assert texts["subtitle"].text == "as of Feb 20, 2026 · calendar: engineering {kept}"
    assert (texts["title"].purpose, texts["subtitle"].purpose) == ("title-text", "subtitle-text")
    # The subtitle is its own typography role, under the title line and inside the same slot.
    title_box, subtitle_box = texts["title"].bounds, texts["subtitle"].bounds
    assert subtitle_box[1] >= title_box[1] + title_box[3] - 0.01
    assert texts["subtitle"].text_layout.font_size < texts["title"].text_layout.font_size
    svg = rendered.artifact.content.decode()
    assert 'data-purpose="subtitle-text"' in svg and "calendar: engineering {kept}" in svg


def _render_in(tmp_path, name: str, heading: dict | None):
    directory = tmp_path / name
    directory.mkdir()
    return _render(directory, heading)


def test_a_title_only_heading_has_no_subtitle_and_a_subtitle_only_heading_keeps_the_project_title(tmp_path):
    only_title = _texts(_render_in(tmp_path, "t", {"title": "Board"}))
    assert only_title["title"].text == "Board" and "subtitle" not in only_title
    only_subtitle = _texts(_render_in(tmp_path, "s", {"subtitle": "{asOf}"}))
    assert only_subtitle["title"].text == "HALCYON" and only_subtitle["subtitle"].text == "Feb 20, 2026"


def test_a_slot_grows_by_the_subtitle_line_so_nothing_overlaps_the_table(tmp_path):
    def title_slot(rendered):
        return next(slot for slot in rendered.surface.slots if slot.source == "title")
    plain = title_slot(_render_in(tmp_path, "p", None))
    headed = title_slot(_render_in(tmp_path, "h", {"subtitle": "x"}))
    assert headed.bounds[3] > plain.bounds[3]


@pytest.mark.parametrize("template", ["{nope}", "{project", "stray } brace"])
def test_an_unknown_placeholder_or_stray_brace_is_a_typed_error(tmp_path, template):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, {"title": template})
    assert "E_VIEW_HEADING_TEMPLATE" in str(caught.value)


def test_a_subtitle_needs_the_themes_subtitle_role(tmp_path):
    def drop(theme: dict) -> None:
        theme["body"]["roles"].pop("subtitle")
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, {"subtitle": "x"}, theme_edit=drop)
    assert "E_THEME_ROLE_REQUIRED" in str(caught.value) or caught.value.diagnostic_id == "E_THEME_ROLE_REQUIRED"


# {calendar} shows the default calendar's declared title, else its id (#1026). No test reads `examples/`.
_WEEK = ["mon", "tue", "wed", "thu", "fri"]


def _render_calendar(tmp_path, name: str, calendar: dict, subtitle: str = "range for {calendar}"):
    directory = tmp_path / name
    directory.mkdir()
    source = _source()
    source["calendars"] = {"engineering": calendar}
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["heading"] = {"subtitle": subtitle}
    return sr.render(directory, source, presentation=parts, actual=ACTUAL)


def test_a_calendar_without_a_title_keeps_rendering_its_id(tmp_path):
    rendered = _render_calendar(tmp_path, "a", {"working_days": _WEEK})
    assert _texts(rendered)["subtitle"].text == "range for engineering"


def test_a_declared_calendar_title_replaces_the_id(tmp_path):
    rendered = _render_calendar(tmp_path, "a", {"title": "launch campaign", "working_days": _WEEK})
    assert _texts(rendered)["subtitle"].text == "range for launch campaign"


def test_a_unicode_calendar_title_renders_as_is(tmp_path):
    title = "Équipe Développement — Ελλάδα Привет"
    rendered = _render_calendar(tmp_path, "a", {"title": title, "working_days": _WEEK})
    assert _texts(rendered)["subtitle"].text == f"range for {title}"


def test_a_calendar_title_is_escaped_in_svg(tmp_path):
    rendered = _render_calendar(tmp_path, "a", {"title": "R&D <A>", "working_days": _WEEK})
    svg = rendered.artifact.content.decode()
    assert "R&amp;D &lt;A&gt;" in svg and "R&D <A>" not in svg


def test_a_long_calendar_title_never_overflows_the_surface(tmp_path):
    title = "a very long calendar title " * 12
    rendered = _render_calendar(tmp_path, "a", {"title": title, "working_days": _WEEK})
    subtitle = _texts(rendered)["subtitle"]
    assert subtitle.text == f"range for {title}" or subtitle.text.endswith("…")
    assert subtitle.bounds[0] + subtitle.bounds[2] <= rendered.surface.canvas_bounds[2] + 0.01


def test_a_calendar_title_changes_nothing_when_no_placeholder_reads_it(tmp_path):
    plain = _render_calendar(tmp_path, "p", {"working_days": _WEEK}, "{project}")
    titled = _render_calendar(tmp_path, "t", {"title": "T", "working_days": _WEEK}, "{project}")
    assert plain.artifact.content == titled.artifact.content
