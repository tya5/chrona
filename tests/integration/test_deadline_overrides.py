"""Per-object View deadline visibility overrides stay separate from Core verdicts (#1397 row 4)."""
from __future__ import annotations

from datetime import date
import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.usecases.draft_render import warning_payloads
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

from test_deadline_mark import MIXED, _marks, _parts, _render, _runs, _source, _ticks


def _with_overrides(show: str, overrides: dict[str, str], *, caption: bool = False) -> dict:
    parts = _parts(show)
    deadlines = {"show": show, "overrides": {key: {"show": value} for key, value in overrides.items()}}
    if caption:
        deadlines["caption"] = {"template": "{daysLate} days late"}
    parts["view"]["body"]["deadlines"] = deadlines
    return parts


def test_overrides_replace_global_show_and_hidden_suppresses_caption_not_core_warning(tmp_path):
    source = _source(**MIXED)
    parts = _with_overrides("slipped", {"a": "hidden", "b": "all", "h": "slipped"}, caption=True)
    rendered = _render(tmp_path, source, parts)

    # Global slipped selects a/g; a is hidden, b's kept deadline is forced in,
    # and h's per-object slipped rule cannot manufacture a W_DEADLINE run.
    assert set(_ticks(rendered)) == {"b", "g"}
    assert set(_runs(rendered)) == {"g"}
    assert _ticks(rendered)["b"].source_ref == "b"
    assert {item["object"] for item in warning_payloads(rendered) if item["code"] == "W_DEADLINE"} == {"a", "g"}


def test_global_all_can_be_narrowed_per_object_and_empty_overrides_match_absence(tmp_path):
    source = _source(**MIXED)
    hidden = _render(tmp_path, source, _with_overrides("all", {"a": "hidden", "b": "slipped"}), name="narrowed")
    plain = _render(tmp_path, source, _parts("all"), name="plain")
    assert set(_ticks(hidden)) == {"g", "h"}
    assert set(_runs(hidden)) == {"g"}

    explicit_empty = _render(tmp_path, source, _with_overrides("all", {}), name="empty")
    assert explicit_empty.surface.primitives == plain.surface.primitives
    assert explicit_empty.artifact.content == plain.artifact.content


def test_override_does_not_select_an_object_or_create_a_missing_deadline(tmp_path):
    source = _source(**MIXED)
    source["objects"]["no-deadline"] = sr.span("no-deadline", date(2026, 1, 1), 10)
    parts = _with_overrides("all", {"b": "all", "no-deadline": "all"})
    parts["view"]["body"]["selection"] = {"include": {"ids": ["a"]}}
    rendered = _render(tmp_path, source, parts)
    assert set(_ticks(rendered)) == {"a"}
    assert not any(item.source_ref in {"b", "no-deadline"} for item in _marks(rendered))


def test_unknown_override_id_fails_even_when_hidden_before_deadline_filtering(tmp_path):
    parts = _with_overrides("slipped", {"not-in-project": "hidden"})
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _source(**MIXED), parts)
    assert raised.value.code == "E_VIEW_DEADLINE_OBJECT_UNKNOWN"
    assert raised.value.source_ref == "/body/deadlines/overrides/not-in-project"


@pytest.mark.parametrize("overrides", [
    {"a": {}},
    {"a": {"show": "later"}},
    {"a": {"show": "hidden", "extra": True}},
])
def test_malformed_override_is_rejected_at_its_view_pointer(tmp_path, overrides):
    parts = _parts("all")
    parts["view"]["body"]["deadlines"]["overrides"] = overrides
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, _source(**MIXED), parts)
    assert raised.value.diagnostic_id == "E_VIEW_SCHEMA"
    assert raised.value.source_ref.startswith("/body/deadlines/overrides")
