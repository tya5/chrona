from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.semantic_mark_facets import select_item_mark_facets
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout import mark_geometry
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.model.projection import ObservationState


DAY = date(2026, 4, 12)


def _item(*, source_type="span", planned=None, actual=None,
          state=ObservationState.UNAVAILABLE, missing_actual_mark="due-end"):
    return SimpleNamespace(
        object_id="task-17", source_type=source_type,
        planned=planned or {"start": DAY, "end": date(2026, 4, 20)},
        actual=actual or {}, observation_state=state,
        missing_actual_mark=missing_actual_mark,
    )


def test_selection_preserves_source_dates_even_for_equal_or_inverted_actuals():
    for actual, expected in (
        ({"start": DAY, "finish": DAY}, (DAY, DAY)),
        ({"start": date(2026, 4, 20), "finish": DAY}, (date(2026, 4, 20), DAY)),
    ):
        selected = select_item_mark_facets(item=_item(actual=actual),
                                           source_kind="combined", as_of=None)
        facet = selected.facets[1]
        assert (facet.facet, facet.semantic_id, facet.shape) == ("actual", "actual", "span")
        assert (facet.start, facet.finish) == expected
        assert selected.source_kind == "combined" and selected.as_of is None


def test_selection_keeps_snapshot_semantic_role_and_actual_only_absence():
    item = _item(source_type="point", planned={"at": DAY},
                 actual={"at": date(2026, 4, 14)})
    snapshot = select_item_mark_facets(item=item, source_kind="snapshot", as_of=DAY)
    assert [(f.facet, f.semantic_id, f.at) for f in snapshot.facets] == [("planned", "snapshot", DAY)]
    actual = select_item_mark_facets(item=item, source_kind="actual", as_of=None)
    assert [(f.facet, f.at) for f in actual.facets] == [("actual", date(2026, 4, 14))]
    assert [(absence.facet, absence.reason) for absence in actual.absences] == [
        ("planned", "actual-only-member")
    ]


@pytest.mark.parametrize("emit_missing", (True, False))
def test_due_missing_actual_keeps_eligibility_and_end_anchor(emit_missing):
    item = _item(state=ObservationState.DUE_UNOBSERVED)
    selected = select_item_mark_facets(item=item, source_kind="primary", as_of=DAY,
                                       emit_missing_actual=emit_missing)
    assert selected.missing_actual_eligible is emit_missing
    assert tuple(f.facet for f in selected.facets) == (
        ("planned", "missing-actual") if emit_missing else ("planned",)
    )
    if emit_missing:
        missing = selected.facets[-1]
        assert (missing.shape, missing.geometry, missing.start, missing.finish) == (
            "span", "end-tick", item.planned["end"], item.planned["end"]
        )


def test_in_progress_missing_actual_retains_original_start_and_as_of():
    start, as_of = date(2026, 4, 8), date(2026, 4, 12)
    item = _item(actual={"start": start, "openUntil": "asOf"}, missing_actual_mark="in-progress")
    selected = select_item_mark_facets(item=item, source_kind="combined", as_of=as_of)
    missing = selected.facets[-1]
    assert (missing.facet, missing.semantic_id, missing.geometry) == (
        "missing-actual", "missing-actual", "in-progress"
    )
    assert (missing.start, missing.finish) == (start, as_of)
    assert item.actual == {"start": start, "openUntil": "asOf"}


@pytest.mark.parametrize(
    ("actual", "as_of", "diagnostic", "reason"),
    [
        ({"start": DAY, "openUntil": "asOf"}, None,
         "W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:task-17", "as-of-required"),
        ({"start": DAY, "openUntil": "asOf"}, DAY,
         "W_LAYOUT_OPEN_ACTUAL_INVALID:task-17", "invalid-open-actual"),
    ],
)
def test_open_actual_absences_and_diagnostic_suppression_are_preserved(actual, as_of, diagnostic, reason):
    item = _item(actual=actual)
    selected = select_item_mark_facets(item=item, source_kind="combined", as_of=as_of)
    assert selected.diagnostics == (diagnostic,)
    assert selected.absences[-1].reason == reason
    silent = select_item_mark_facets(item=item, source_kind="combined", as_of=as_of,
                                     emit_diagnostics=False)
    assert silent.diagnostics == () and silent.absences == selected.absences


@pytest.mark.parametrize(
    ("source_kind", "state", "actual", "reason"),
    [
        ("primary", ObservationState.RECORDED, {}, "recorded-on-companion-member"),
        ("primary", ObservationState.UNAVAILABLE, {"progress": 0.5}, "incomplete-observation"),
        ("primary", ObservationState.UNAVAILABLE, {}, "no-selected-observation"),
        ("snapshot", ObservationState.UNAVAILABLE, {}, "member-has-no-actual-facet"),
    ],
)
def test_nonselected_actual_reasons_remain_distinct(source_kind, state, actual, reason):
    selected = select_item_mark_facets(item=_item(state=state, actual=actual),
                                       source_kind=source_kind, as_of=None)
    assert selected.absences[-1].reason == reason


class _ShapeTheme:
    def variant_symbol(self, _role):
        return {"shape": "diamond"}


_KIND_EXPECTED = {
    "planned": (("planned", "planned"),),
    "primary": (("planned", "planned"),),
    "combined": (("planned", "planned"), ("actual", "actual")),
    "actual": (("actual", "actual"),),
    "snapshot": (("planned", "snapshot"),),
    "scenario": (("planned", "snapshot"),),
}


@pytest.mark.parametrize("source_type", ("point", "span"))
@pytest.mark.parametrize("source_kind", tuple(_KIND_EXPECTED))
def test_composer_characterizes_each_source_kind_and_temporal_shape(source_kind, source_type, monkeypatch):
    origin = date(2026, 1, 1)
    planned = ({"at": date(2026, 1, 3)} if source_type == "point" else
               {"start": date(2026, 1, 3), "end": date(2026, 1, 6)})
    actual = ({"at": date(2026, 1, 5)} if source_type == "point" else
              {"start": date(2026, 1, 5), "finish": date(2026, 1, 8)})
    item = SimpleNamespace(
        object_id="item", title="Item", source_type=source_type,
        planned=planned, actual=actual, observation_state=ObservationState.RECORDED,
        missing_actual_mark="due-end",
    )
    frame = MarkBandFrame.zero_origin(
        ScalePlacement("surface", "test", origin, date(2026, 1, 20), 0, 100, 10, 2),
        50,
        {
            "planned": MarkGeometry(.2, .1, 1, 0),
            "snapshot": MarkGeometry(.4, .3, 2, 0),
            "actual": MarkGeometry(.4, .5, 3, 0, symbol_height=.12, symbol_offset=.72),
            "missing-actual": MarkGeometry(.2, .8, 4, 0),
        },
    )

    result = compose_item_marks(item=item, instance_id="item", source_kind=source_kind,
                                frame=frame, as_of=date(2026, 1, 10),
                                theme_tokens=_ShapeTheme(), slot_id="timeline")
    expected = []
    for facet, semantic in _KIND_EXPECTED[source_kind]:
        if facet == "actual" and source_kind == "actual":
            selected_type = "point" if source_type == "point" else "span"
        else:
            selected_type = source_type
        shape = "point" if selected_type == "point" else "span"
        if selected_type == "point":
            x = 18.0 if semantic == "actual" else 14.0
            if semantic == "snapshot":
                y, size = 15.0, 20.0
            elif semantic == "actual":
                y, size = 36.0, 6.0
            else:
                y, size = 5.0, 10.0
            bounds = (x - size / 2, y, size, size)
            port = (x, y + size / 2)
        else:
            x = 18.0 if semantic == "actual" else 14.0
            width = 6.0
            if semantic == "snapshot":
                y, height = 15.0, 20.0
            elif semantic == "actual":
                y, height = 25.0, 20.0
            else:
                y, height = 5.0, 10.0
            bounds = (x, y, width, height)
            port = (x, y + height / 2)
            end_port = (x + width, y + height / 2)
        expected.append((f"{facet}:item", semantic, shape, bounds, port,
                         port if shape == "point" else end_port,
                         100 + {"planned": 1, "snapshot": 2, "actual": 3}[semantic]))

    actual_marks = [
        (mark.placement_id, mark.semantic_id, mark.mark_shape,
         (float(mark.bounds.inline), float(mark.bounds.block),
          float(mark.bounds.inline_size), float(mark.bounds.block_size)),
         mark.start_port, mark.end_port, mark.paint_order)
        for mark in result.marks
    ]
    assert actual_marks == expected
    selected = select_item_mark_facets(item=item, source_kind=source_kind,
                                      as_of=date(2026, 1, 10))

    def no_reselection(**_kwargs):
        pytest.fail("a prepared source selection must not be recomputed")

    monkeypatch.setattr(mark_geometry, "select_item_mark_facets", no_reselection)
    prepared = compose_item_marks(item=item, instance_id="item", source_kind=source_kind,
                                  frame=frame, as_of=date(2026, 1, 10),
                                  theme_tokens=_ShapeTheme(), slot_id="timeline",
                                  selection=selected)
    assert prepared == result
    with pytest.raises(LayoutError, match="selection-mismatch"):
        compose_item_marks(item=item, instance_id="item", source_kind=source_kind,
                           frame=frame, as_of=None, theme_tokens=_ShapeTheme(),
                           slot_id="timeline", selection=selected)


def test_prepared_selection_suppresses_preflight_diagnostics_without_reselection(monkeypatch):
    item = _item(actual={"start": DAY, "openUntil": "asOf"})
    selection = select_item_mark_facets(item=item, source_kind="combined", as_of=None)
    assert selection.diagnostics == ("W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:task-17",)
    frame = MarkBandFrame.zero_origin(
        ScalePlacement("surface", "test", DAY, date(2026, 4, 30), 0, 100, 0, 2),
        50, {role: MarkGeometry(.2, .1, 1, 0)
             for role in ("planned", "actual", "missing-actual")},
    )

    def no_reselection(**_kwargs):
        pytest.fail("preflight must reuse the prepared source selection")

    monkeypatch.setattr(mark_geometry, "select_item_mark_facets", no_reselection)
    kwargs = dict(item=item, instance_id="instance", source_kind="combined", frame=frame,
                  as_of=None, theme_tokens=_ShapeTheme(), slot_id="timeline", selection=selection)
    final = compose_item_marks(**kwargs)
    preflight = compose_item_marks(**kwargs, emit_diagnostics=False)
    assert final.diagnostics == selection.diagnostics
    assert final.diagnostic_provenance
    assert preflight.diagnostics == preflight.diagnostic_provenance == ()
    assert preflight.marks == final.marks
    assert preflight.absences == final.absences == selection.absences
