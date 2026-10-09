from pathlib import Path

import pytest

from chrona.presentation.model.placement_candidates import (
    _parse_connector, _parse_obstacles, _parse_region, _parse_search,
    candidate_order, legacy_candidate, legacy_candidate_order, parse_candidate, parse_candidates,
)


def test_legacy_rungs_expand_to_four_typed_parts_without_reordering() -> None:
    candidates, ladder = legacy_candidate_order("note", ("above", "rail", "suppress"), "end")
    assert ladder == ("end", "above", "rail", "suppress")
    assert tuple(item.candidate_id for item in candidates) == ("end", "above", "rail")
    assert candidates[0].region.kind == "side"
    assert candidates[0].search.kind == "adjacent"
    assert candidates[0].search.side == "end"
    assert "dependency-route" in candidates[0].obstacles.classes
    assert candidates[0].connector.kind == "leader"
    assert candidates[-1].region.source == "annotations"
    assert candidates[-1].search.kind == "row-aligned"


def test_highlight_has_no_connector_and_suppress_is_not_a_candidate() -> None:
    candidates, ladder = legacy_candidate_order("highlight", ("rail", "suppress"))
    assert ladder == ("rail", "suppress")
    assert len(candidates) == 1
    assert candidates[0].connector.kind == "none"


def test_layout_order_consumes_normalized_candidates_and_inserts_preference() -> None:
    normalized, _ = legacy_candidate_order("note", ("above", "rail", "suppress"))
    candidates, ladder = candidate_order(normalized, "note", ("above", "rail", "suppress"), "end")
    assert ladder == ("end", "above", "rail", "suppress")
    assert candidates[1] is normalized[0]
    assert candidates[2] is normalized[1]
    assert candidates[0].candidate_id == "end"


def test_review_normalization_does_not_import_layout_candidate_implementation() -> None:
    source = (Path(__file__).resolve().parents[5] / "src/chrona/presentation/review/v05_content.py").read_text()
    assert "chrona.presentation.layout.placement_candidates" not in source


def _bad(call, *needles: str) -> None:
    with pytest.raises(ValueError) as caught:
        call()
    message = str(caught.value)
    assert message.startswith("E_PRESENTATION_CANDIDATE_INVALID: "), message
    for needle in needles:
        assert needle in message, message


def _candidate(**changes):
    raw = {
        "id": "candidate-a",
        "region": {"kind": "slot", "source": "annotations"},
        "search": {"kind": "adjacent", "side": "above"},
        "obstacles": {"classes": ["mark", "text"]},
        "connector": {"kind": "leader"},
    }
    raw.update(changes)
    return raw


@pytest.mark.parametrize("call,needles", [
    (lambda: legacy_candidate("diagonal", "note"), ("'diagonal'", "expected rail, above, below, start or end")),
    (lambda: _parse_region({"kind": "mystery"}), ("region.kind='mystery'", "plot", "slot")),
    (lambda: _parse_region({"kind": "intersection", "of": [{"kind": "plot"}]}), ("region.of", "length 1", "exactly 2")),
    (lambda: _parse_region({"kind": "slot", "source": 17}), ("region.source=17", "string source")),
    (lambda: _parse_search({"kind": "diagonal"}), ("search.kind='diagonal'", "nearest-free")),
    (lambda: _parse_search({"kind": "adjacent", "side": "inside"}), ("search.side='inside'", "above", "end")),
    (lambda: _parse_search({"kind": "adjacent", "side": "above", "maxPositions": 0}), ("maxPositions=0", "1 through 1024")),
    (lambda: _parse_search({"kind": "nearest-free", "maxInlineEm": False}), ("maxInlineEm=False", "positive number")),
    (lambda: _parse_search({"kind": "adjacent", "side": "above", "maxInlineEm": 2}), ("maxInlineEm=2", "only valid for nearest-free")),
    (lambda: _parse_obstacles({"classes": []}, search_kind="adjacent"), ("classes=list of length 0", "nonempty")),
    (lambda: _parse_obstacles({"classes": ["mark", 7]}, search_kind="adjacent"), ("classes[1]=7", "must be a string")),
    (lambda: _parse_obstacles({"classes": ["mark", "mark"]}, search_kind="adjacent"), ("classes[1]='mark'", "duplicates")),
    (lambda: _parse_obstacles({"classes": ["mark"]}, search_kind="nearest-free"), ("omits required shared classes", "text")),
    (lambda: _parse_connector({"kind": "wire"}), ("connector.kind='wire'", "leader", "tail")),
    (lambda: parse_candidate(_candidate(id="")), ("candidate.id=''", "nonempty string")),
    (lambda: parse_candidate(_candidate(region=[])), ("candidate id 'candidate-a'", "region=list of length 0", "type list")),
    (lambda: parse_candidate(_candidate(search={"kind": "row-aligned"}, connector={"kind": "tail"})),
     ("candidate id 'candidate-a'", "tail", "row-aligned", "nearest-free or adjacent")),
    (lambda: parse_candidates([]), ("candidates=list of length 0", "nonempty")),
    (lambda: parse_candidates([_candidate(id="same"), _candidate(id="same")]), ("candidate id 'same'", "more than once")),
])
def test_invalid_candidate_intent_names_the_offending_operand_and_expected_form(call, needles):
    _bad(call, *needles)
