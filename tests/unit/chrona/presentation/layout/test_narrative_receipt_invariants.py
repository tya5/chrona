"""Typed completed narrative identity and closure invariants (#1346)."""
from dataclasses import FrozenInstanceError, replace

import pytest

from chrona.presentation.layout.surface_quality import NarrativeReceipt, SurfacePlacement


@pytest.mark.parametrize("change", [
    {"kind": "index"}, {"form": "status"}, {"source_id": ""}, {"source_id": 1},
    {"placement_id": ""}, {"placement_id": None}, {"occurrence_index": -1},
    {"occurrence_index": True}, {"occurrence_index": 0.5},
    {"occurrence_index": 1}, {"kind": "note", "form": "summary"},
])
def test_receipt_rejects_non_narrative_or_untyped_identity(change):
    with pytest.raises(ValueError):
        NarrativeReceipt(**{"kind": "annotation", "source_id": "source", "placement_id": "completed", **change})


def test_receipt_is_frozen_and_its_identity_does_not_depend_on_text_id_or_form():
    body = NarrativeReceipt("annotation", "occurrence", "arbitrary-completed-id")
    summary = replace(body, placement_id="another-completed-id", form="summary")
    assert body.identity == summary.identity == ("annotation", "occurrence", 0)
    with pytest.raises(FrozenInstanceError):
        body.source_id = "changed"
    assert NarrativeReceipt("note", "same-source", "a", occurrence_index=0).identity != NarrativeReceipt(
        "note", "same-source", "b", occurrence_index=1).identity
    # Project annotation-map keys have no minLength contract. Index identity
    # closes even an empty unconsumed note key, without narrowing that schema.
    assert NarrativeReceipt("note", "", "note:").identity == ("note", "", 0)


def test_completion_rejects_receipts_without_their_completed_text():
    with pytest.raises(ValueError, match="uncompleted narrative"):
        SurfacePlacement(narrative_receipts=(NarrativeReceipt("annotation", "n", "absent"),)).assert_valid()


def test_one_annotation_cannot_be_counted_as_both_body_and_summary():
    body = NarrativeReceipt("annotation", "n", "body")
    with pytest.raises(ValueError, match="duplicate"):
        SurfacePlacement(narrative_receipts=(body, replace(body, form="summary", placement_id="summary"))).assert_valid()
