"""#1134: a Theme that holds ground text at `error` accepts one named pair, proven through a real render.

The fixture is the one of #1126: a member label lies on an accent period band and misses the ground-text floor
(4.44 against 4.5). No corpus slide can change what these tests prove.
"""
from __future__ import annotations

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.integration.test_contrast_opt_in_render import _render

PAIR = {"purpose": "member-label", "over": "any", "minimum": 4.0, "reason": "Owner-approved label on the accent band"}


def _policy(*exceptions):
    return {"groundText": "error", "exceptions": list(exceptions)}


def _codes(rendered):
    return [item.payload["code"] for item in rendered.warning_records]


def test_an_accepted_pair_renders_with_a_typed_warning_that_records_the_reason(tmp_path):
    rendered = _render(tmp_path, _policy(PAIR))

    (record,) = [item for item in rendered.warning_records if item.payload["code"] == "W_SCENE_CONTRAST_ACCEPTED"]
    payload = record.payload
    assert (payload["severity"], payload["findingCode"]) == ("warning", "E_SCENE_STATE_TEXT_CONTRAST")
    assert payload["measuredFacts"]["exceptionMinimum"] == 4.0
    assert payload["measuredFacts"]["exceptionReason"] == PAIR["reason"]
    assert payload["measuredFacts"]["contrastRatio"] < 4.5
    assert record.identity in rendered.scene.diagnostics
    assert "W_SCENE_CONTRAST_EXCEPTION_UNUSED" not in _codes(rendered)


def test_a_pair_below_the_declared_minimum_still_fails_the_render(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _policy({**PAIR, "minimum": 4.4999}))

    assert raised.value.code == "E_SCENE_STATE_TEXT_CONTRAST"


def test_an_entry_that_matches_nothing_accepts_nothing_so_the_miss_still_fails(tmp_path):
    with pytest.raises(RenderFailed):
        _render(tmp_path, _policy({**PAIR, "purpose": "no-such-purpose"}))


def test_an_unused_entry_is_a_warning_when_nothing_needed_it(tmp_path):
    rendered = _render(tmp_path, {"groundText": "none", "exceptions": [PAIR]})

    unused = [item for item in rendered.warning_records if item.payload["code"] == "W_SCENE_CONTRAST_EXCEPTION_UNUSED"]
    assert len(unused) == 1 and unused[0].payload["disposition"] == "exceptions[0]"


def test_the_accepted_picture_equals_the_picture_without_a_policy(tmp_path):
    accepted = _render(tmp_path, _policy(PAIR), name="a")
    default = _render(tmp_path, name="b")

    assert accepted.artifact.content == default.artifact.content
