from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrence, MarkOccurrenceKind, build_item_mark_visibility_index,
)
from chrona.presentation.layout.window_relation_admission import (
    WindowRelationEndpointAbsence, complete_window_relation_endpoint_absence,
)
from chrona.presentation.model.projection import WindowMode
from tests.unit.chrona.presentation.layout.test_lane_window_marks import _fixture


def _admit(projection, index, endpoint, kind=MarkOccurrenceKind.LANE_FINAL):
    occurrence = MarkOccurrence(kind, "lane" if kind == MarkOccurrenceKind.LANE_FINAL else "source-row",
                                "item", "object", projection.rows[0].items[0].source_kind)
    return complete_window_relation_endpoint_absence(
        occurrence, endpoint, projection=projection, as_of=None, visibility_index=index)


@pytest.mark.parametrize("endpoint", ["start", "at", "end", "finish"])
def test_wholly_omitted_original_endpoint_has_cache_identical_nonspatial_proof(endpoint, monkeypatch):
    projection, index = _fixture()
    monkeypatch.setattr("chrona.presentation.layout.surface_mark_visibility.select_item_mark_facets",
                        lambda **kwargs: pytest.fail("relation admission must not reselect source facts"))
    proof = _admit(projection, index, endpoint)
    assert proof.reason == "outside-window"
    assert proof.occurrence.object_id == "object"
    assert proof.source_ref == "/projection/rows/source-row/items/item"
    assert proof.visibility is index.lookup(proof.occurrence, projection=projection, as_of=None)
    assert proof.visibility is _admit(projection, index, endpoint, MarkOccurrenceKind.LANE_SOURCE).visibility
    assert not hasattr(proof, "bounds") and not hasattr(proof, "port")


@pytest.mark.parametrize("start,end,blocked", [(1, 4, "start"), (4, 6, "end")])
def test_clipped_host_preserves_only_original_visible_ports(start, end, blocked):
    projection, _ = _fixture()
    item = replace(projection.rows[0].items[0],
                   planned={"start": date(2026, 2, start), "end": date(2026, 2, end)})
    projection = replace(projection, rows=(replace(projection.rows[0], items=(item,)),),
                         lane_rows=(replace(projection.lane_rows[0], items=(item,)),))
    index = build_item_mark_visibility_index(projection, as_of=None)
    assert _admit(projection, index, blocked) is not None
    assert _admit(projection, index, "end" if blocked == "start" else "start") is None


@pytest.mark.parametrize("mode", [WindowMode.EXPLICIT, WindowMode.SELECTED_PLANNED])
def test_containing_and_derived_windows_have_no_endpoint_absence(mode):
    projection, index = _fixture(mode=mode, window=(date(2026, 1, 1), date(2026, 3, 1)))
    assert _admit(projection, index, "start") is None
    assert _admit(projection, index, "end") is None


def test_copied_visibility_or_visible_endpoint_cannot_forge_absence():
    projection, index = _fixture()
    proof = _admit(projection, index, "start")
    with pytest.raises(LayoutError, match="invalid-source-proof"):
        replace(proof, visibility=replace(proof.visibility))
    projection, index = _fixture(window=(date(2026, 1, 1), date(2026, 3, 1)))
    occurrence = MarkOccurrence(MarkOccurrenceKind.LANE_FINAL, "lane", "item", "object", "combined")
    with pytest.raises(LayoutError, match="invalid-source-proof"):
        WindowRelationEndpointAbsence(occurrence, "end",
            index.lookup(occurrence, projection=projection, as_of=None), index)


def test_stale_request_and_unknown_occurrence_fail_closed():
    projection, index = _fixture()
    with pytest.raises(LayoutError, match="request-mismatch"):
        _admit(replace(projection, window_mode=WindowMode.SELECTED_PLANNED), index, "start")
    occurrence = MarkOccurrence(MarkOccurrenceKind.LANE_FINAL, "missing", "item", "object", "combined")
    with pytest.raises(LayoutError, match="missing-source-occurrence"):
        complete_window_relation_endpoint_absence(occurrence, "end", projection=projection,
            as_of=None, visibility_index=index)


@pytest.mark.parametrize("day,omitted", [(3, False), (5, True)])
def test_point_ports_use_half_open_window_without_substitute_endpoint(day, omitted):
    projection, _ = _fixture()
    item = replace(projection.rows[0].items[0], source_type="point",
                   planned={"at": date(2026, 2, day)}, actual=None)
    projection = replace(projection, rows=(replace(projection.rows[0], items=(item,)),),
                         lane_rows=(replace(projection.lane_rows[0], items=(item,)),))
    index = build_item_mark_visibility_index(projection, as_of=None)
    for endpoint in ("at", "start", "end", "finish"):
        assert (_admit(projection, index, endpoint) is not None) is omitted


def test_absent_planned_facet_is_not_a_window_omission_claim():
    projection, index = _fixture(source_kind="actual")
    assert _admit(projection, index, "start") is None
    assert _admit(projection, index, "end") is None
