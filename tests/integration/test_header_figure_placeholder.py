"""#586 I586-3: a derived figure inside a group-header text, rendered end to end.

A synthetic Project goes through the packaged `control-room-dark` bundle (grouped by `owner`, header
presentation). No `examples/` input.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderRejected
from tests.support import synthetic_review as sr

OWNERS = ("bus", "payload", "ground")
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}
COUNTDOWN = {"id": "countdown", "kind": "daysUntil", "to": {"object": "launch", "endpoint": "at"}}


def _project() -> dict:
    objects = {f"t-{owner}": sr.span(f"t-{owner}", date(2026, 1, 5) + timedelta(days=index * 3), 14, owner=owner)
               for index, owner in enumerate(OWNERS)}
    objects["launch"] = sr.point("launch", date(2026, 3, 20), owner="bus")
    source = sr.project(objects)
    for owner in OWNERS:
        source["entities"][owner]["title"] = owner.title()
    return source


def _render(tmp_path, header, *figures, actual=ACTUAL):
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["grouping"]["header"] = deepcopy(header)
    if figures:
        parts["view"]["body"]["figures"] = [deepcopy(item) for item in figures]
    return sr.render(tmp_path, _project(), presentation=parts, actual=actual)


def _headers(rendered) -> list[str]:
    return [item.text for item in rendered.surface.primitives if item.scene_id.startswith("group-header:")]


def test_a_header_shows_a_declared_figure(tmp_path):
    headers = _headers(_render(tmp_path, {"text": "{ordinal} {title} · {figure:countdown} DAYS"}, COUNTDOWN))
    # 2026-02-20 to 2026-03-20: February 2026 has 28 days. The figure is the same in every group's header.
    assert headers == ["1 Bus · 28 DAYS", "2 Payload · 28 DAYS", "3 Ground · 28 DAYS"]


def test_the_first_group_template_may_show_a_figure_too(tmp_path):
    header = {"text": "{title}", "first": "{title} · {figure:countdown} DAYS"}
    assert _headers(_render(tmp_path, header, COUNTDOWN)) == ["Bus · 28 DAYS", "Payload", "Ground"]


def test_a_past_target_shows_its_sign(tmp_path):
    since = {"id": "since", "kind": "daysUntil", "from": {"object": "launch", "endpoint": "at"}, "to": "asOf"}
    assert _headers(_render(tmp_path, {"text": "{title} {figure:since}"}, since))[0] == "Bus -28"


def test_two_figures_and_literal_braces_compose(tmp_path):
    working = {"id": "working", "kind": "daysUntil", "to": {"object": "launch", "endpoint": "at"}, "days": "working"}
    source = _project()
    source["project"]["calendar"] = "standard"
    source["calendars"] = {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}}
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["grouping"]["header"] = {"text": "{{{figure:countdown}d / {figure:working}wd}}"}
    parts["view"]["body"]["figures"] = [COUNTDOWN, working]
    rendered = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL)
    assert _headers(rendered)[0] == "{28d / 20wd}"


def test_a_header_without_a_figure_placeholder_ignores_declared_figures(tmp_path):
    (tmp_path / "plain").mkdir()
    (tmp_path / "declared").mkdir()
    header = {"text": "{ordinal} {title}"}
    assert (_headers(_render(tmp_path / "declared", header, COUNTDOWN))
            == _headers(_render(tmp_path / "plain", header)))


def test_a_placeholder_naming_an_undeclared_figure_is_refused_at_the_contract(tmp_path):
    with pytest.raises(ClosureError) as failure:
        _render(tmp_path, {"text": "{title} {figure:missing}"}, COUNTDOWN)
    assert failure.value.diagnostic_id == "E_VIEW_GROUP_HEADER_TEMPLATE"
    assert "missing" in failure.value.detail and "declared: countdown" in failure.value.detail


def test_a_placeholder_when_the_view_declares_no_figures_says_none(tmp_path):
    with pytest.raises(ClosureError) as failure:
        _render(tmp_path, {"text": "{figure:countdown}"})
    assert failure.value.diagnostic_id == "E_VIEW_GROUP_HEADER_TEMPLATE" and "declared: none" in failure.value.detail


def test_the_first_template_is_checked_too(tmp_path):
    with pytest.raises(ClosureError) as failure:
        _render(tmp_path, {"text": "{title}", "first": "{figure:ghost}"}, COUNTDOWN)
    assert failure.value.diagnostic_id == "E_VIEW_GROUP_HEADER_TEMPLATE"


def test_a_figure_with_a_missing_fact_refuses_the_render_instead_of_a_blank_header(tmp_path):
    missing_period = {"id": "countdown", "kind": "daysUntil", "to": {"period": "nowhere", "side": "start"}}
    with pytest.raises(RenderRejected) as failure:
        _render(tmp_path, {"text": "{title} {figure:countdown}"}, missing_period)
    assert [item.id for item in failure.value.diagnostics] == ["E_FIGURE_PERIOD_UNKNOWN"]
    (tmp_path / "asof").mkdir()
    with pytest.raises(RenderRejected) as failure:
        _render(tmp_path / "asof", {"text": "{title} {figure:countdown}"}, COUNTDOWN, actual=None)
    assert [item.id for item in failure.value.diagnostics] == ["E_FIGURE_ASOF_MISSING"]
