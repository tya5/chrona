from pathlib import Path

from chrona.presentation.model.placement_candidates import candidate_order, legacy_candidate_order


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
