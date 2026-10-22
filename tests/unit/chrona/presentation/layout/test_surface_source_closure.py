from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout import surface_source_closure as closure
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.source_use import (
    CompletedSourceUse,
    SourceConsumer,
    SourceDestinationActivation,
    SourceTextUse,
)
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.sources import MeasuredLegend, MeasuredLegendEntry
from chrona.presentation.layout.sources import SourceInput
from chrona.presentation.model.surface_content import SurfaceLegendEntry


def _use(content="A", block=10, *, lines=None, available_inline=None,
         consumer_inline=20, geometry_witness=()):
    text = TextPlacement(
        "annotation-text:1", "annotation-1", content,
        Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(10)), "annotation",
        lines=lines if lines is not None else (content,), font_family="Test Sans", font_size=10,
        line_height=1, font_asset_identity="font:test",
    )
    consumer = SourceConsumer("annotation-1", "list", Decimal(20), Decimal(block),
                              (SourceTextUse.from_placement(text, available_inline=available_inline),),
                              geometry_witness=geometry_witness)
    consumer = SourceConsumer(consumer.consumer_id, consumer.disposition, Decimal(consumer_inline),
                              consumer.block_size, consumer.text, consumer.treatment,
                              consumer.geometry_witness)
    return CompletedSourceUse(annotations=(consumer,))


@dataclass(frozen=True)
class _Composition:
    source_use: CompletedSourceUse | None
    marker: str = "accepted"


def _value():
    return SimpleNamespace(profile={"root": {"id": "original"}}, progress=None)


def _prepared_plan(source_use=None, *, entries=None, annotation_input=None):
    entries = source_use.legend_entries if entries is None and source_use is not None else (entries or ())
    if annotation_input is None:
        annotation_input = (source_use.annotation_input() if source_use is not None
                            else SourceInput(content_present=False))
    measured = SimpleNamespace(
        inputs={"annotations": annotation_input},
        legend_layout=source_use.legend_layout if source_use is not None else None)
    return SimpleNamespace(source_use=source_use, activated=False, measured=measured,
                           measured_legend_entries=entries,
                           content=SimpleNamespace(legend_entries=entries), preparation=None)


def test_source_demand_converges_only_after_preparation_uses_exact_observed_demand(monkeypatch):
    calls = []

    def prepare(value, *, source_use=None, activate_annotations=False):
        plan = _prepared_plan(source_use)
        plan = SimpleNamespace(**{**vars(plan), "activated": activate_annotations})
        calls.append((value.profile, source_use, activate_annotations, plan))
        return plan

    monkeypatch.setattr(closure, "prepare_surface_render_plan", prepare)
    observed = _use()

    def compose(value, plan):
        return _Composition(observed)

    plan, composition = closure.complete_source_render_plan(_value(), compose)

    assert composition.source_use == observed
    assert plan.source_use == observed
    assert len(calls) == 2
    assert all(profile is calls[0][0] for profile, *_ in calls)
    assert calls[0][1:3] == (None, False)
    assert calls[1][1:3] == (observed, False)


def test_same_finite_content_with_drifting_block_demand_is_unstable(monkeypatch):
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda value, *, source_use=None, activate_annotations=False:
                        _prepared_plan(source_use))
    sequence = iter((_use(block=10), _use(block=16)))

    with pytest.raises(LayoutError) as caught:
        closure.complete_source_render_plan(_value(),
            lambda value, plan: _Composition(next(sequence)))

    assert caught.value.diagnostic_id == "E_LAYOUT_SOURCE_CONTENT_UNSTABLE"


@pytest.mark.parametrize("first,second", (
    (_use(consumer_inline=20), _use(consumer_inline=24)),
    (_use(geometry_witness=("insets", Decimal(2), Decimal(3))),
     _use(geometry_witness=("insets", Decimal(4), Decimal(3)))),
))
def test_numeric_witness_drift_with_same_finite_state_is_unstable(monkeypatch, first, second):
    assert first.finite_state() == second.finite_state()
    assert first != second
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda value, *, source_use=None, activate_annotations=False:
                        (_prepared_plan(source_use) if first.annotations[0].geometry_witness == ()
                         else SimpleNamespace(source_use=source_use, activated=activate_annotations)))
    sequence = iter((first, second))

    with pytest.raises(LayoutError) as caught:
        closure.complete_source_render_plan(_value(),
            lambda value, plan: _Composition(next(sequence)))

    assert caught.value.diagnostic_id == "E_LAYOUT_SOURCE_CONTENT_UNSTABLE"


def test_allocation_only_drift_accepts_current_prepared_measurement(monkeypatch):
    first = _use(available_inline=Decimal("191.31"))
    final = _use(available_inline=Decimal("174.664"))
    assert first.finite_state() == final.finite_state()
    calls = []

    def prepare(value, *, source_use=None, activate_annotations=False):
        # Allocation may differ from the prior observation while the actual
        # measured source input remains exactly equal.
        plan = _prepared_plan(source_use)
        calls.append((source_use, plan))
        return plan

    monkeypatch.setattr(closure, "prepare_surface_render_plan", prepare)
    observed = iter((first, final))
    plan, composition = closure.complete_source_render_plan(
        _value(), lambda value, candidate: _Composition(next(observed)))

    assert len(calls) == 2
    assert plan.measured.inputs["annotations"] == final.annotation_input()
    assert plan.measured.inputs["annotations"] == composition.source_use.annotation_input()
    assert composition.source_use == final


def test_repeated_finite_state_cycle_a_b_a_is_unstable(monkeypatch):
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda value, *, source_use=None, activate_annotations=False:
                        SimpleNamespace(source_use=source_use, activated=activate_annotations))
    sequence = iter((_use("A"), _use("B"), _use("A")))

    with pytest.raises(LayoutError) as caught:
        closure.complete_source_render_plan(_value(),
            lambda value, plan: _Composition(next(sequence)))

    assert caught.value.diagnostic_id == "E_LAYOUT_SOURCE_CONTENT_UNSTABLE"
    assert "repeats" in str(caught.value).lower()


def test_changed_line_partition_is_a_new_finite_state_and_can_converge(monkeypatch):
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda value, *, source_use=None, activate_annotations=False:
                        SimpleNamespace(source_use=source_use, activated=activate_annotations))
    initial_partition = _use("AB", lines=("AB",))
    completed_partition = _use("AB", lines=("A", "B"))
    assert initial_partition.finite_state() != completed_partition.finite_state()
    sequence = iter((initial_partition, completed_partition, completed_partition))

    plan, composition = closure.complete_source_render_plan(
        _value(), lambda value, plan: _Composition(next(sequence)))

    assert composition.source_use == completed_partition
    assert plan.source_use == completed_partition


def test_source_destination_activation_retries_only_after_actual_activation(monkeypatch):
    calls = []

    def prepare(value, *, source_use=None, activate_annotations=False):
        has_closed_annotations = bool(source_use and source_use.annotations)
        plan = SimpleNamespace(source_use=source_use,
                               activated=activate_annotations,
                               annotations_slot=has_closed_annotations or activate_annotations)
        calls.append((value.profile, source_use, activate_annotations, plan))
        return plan

    monkeypatch.setattr(closure, "prepare_surface_render_plan", prepare)
    value = _value()

    def compose(value, plan):
        if not plan.annotations_slot:
            raise SourceDestinationActivation("annotations", "annotation-1", "list-row")
        return _Composition(_use())

    plan, composition = closure.complete_source_render_plan(value, compose)

    assert not plan.activated
    assert plan.annotations_slot
    assert composition.source_use == _use()
    assert len(calls) == 3
    assert all(profile is value.profile for profile, *_ in calls)
    assert [activated for _, _, activated, _ in calls] == [False, True, False]
    assert calls[2][1] == composition.source_use
    assert calls[2][3].annotations_slot


def test_repeated_activation_without_a_closed_consumer_is_unstable(monkeypatch):
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda value, *, source_use=None, activate_annotations=False:
                        SimpleNamespace(activated=activate_annotations,
                                        annotations_slot=activate_annotations))

    with pytest.raises(LayoutError) as caught:
        closure.complete_source_render_plan(_value(),
            lambda value, plan: (_ for _ in ()).throw(
                SourceDestinationActivation("annotations", "annotation-1", "list-row")))

    assert caught.value.diagnostic_id == "E_LAYOUT_SOURCE_CONTENT_UNSTABLE"
    assert "activation" in str(caught.value).lower()


def test_declaring_destination_alone_does_not_activate_it(monkeypatch):
    calls = []

    def prepare(value, *, source_use=None, activate_annotations=False):
        calls.append(activate_annotations)
        return SimpleNamespace(activated=activate_annotations)

    monkeypatch.setattr(closure, "prepare_surface_render_plan", prepare)
    value = SimpleNamespace(profile={"root": {"id": "original"}}, declared_destinations=("annotations",))

    plan, _ = closure.complete_source_render_plan(value,
        lambda value, plan: _Composition(CompletedSourceUse()))

    # The first observed empty witness is still a new source measurement and
    # gets one exact re-preparation; declaration alone never requests activation.
    assert calls == [False, False]
    assert not plan.activated


def _initial_plan(entries, legend_layout):
    from chrona.presentation.layout.sources import SourceInput
    measured = SimpleNamespace(
        inputs={"annotations": SourceInput(content_present=False)},
        legend_layout=legend_layout)
    return SimpleNamespace(content=SimpleNamespace(legend_entries=entries), measured=measured)


def test_initial_no_annotation_plan_with_exact_full_legend_witness_is_already_closed(monkeypatch):
    entries = (SurfaceLegendEntry("actual", "Actual"),
               SurfaceLegendEntry("planned", "Planned"))
    layout = MeasuredLegend(
        (MeasuredLegendEntry(("Actual",), Decimal(0), Decimal(0), Decimal(20),
                             Decimal(12), Decimal(80), Decimal(12), source_text="Actual"),
         MeasuredLegendEntry(("Planned",), Decimal(0), Decimal(12), Decimal(24),
                             Decimal(12), Decimal(76), Decimal(12), source_text="Planned")),
        Decimal(24), entries, Decimal(100), Decimal(100))
    initial = _initial_plan(entries, layout)
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda *args, **kwargs: pytest.fail("exact initial witness should not reprepare"))

    plan, composition = closure.complete_source_render_plan(
        _value(), lambda value, plan: _Composition(CompletedSourceUse(entries, layout, ())),
        initial=initial)

    assert plan is initial
    assert composition.source_use == CompletedSourceUse(entries, layout, ())


def test_same_legend_entry_count_with_different_identity_is_not_already_closed(monkeypatch):
    initial_entry = SurfaceLegendEntry("actual", "Actual")
    observed_entry = SurfaceLegendEntry("planned", "Planned")
    initial = _initial_plan((initial_entry,), None)
    calls = []

    def prepare(value, *, source_use=None, activate_annotations=False):
        calls.append((source_use, activate_annotations))
        return SimpleNamespace(source_use=source_use)

    monkeypatch.setattr(closure, "prepare_surface_render_plan", prepare)
    observed = CompletedSourceUse((observed_entry,), None, ())

    plan, composition = closure.complete_source_render_plan(
        _value(), lambda value, plan: _Composition(observed), initial=initial)

    assert len(calls) == 1
    assert calls[0] == (observed, False)
    assert plan is not initial
    assert composition.source_use == observed


def test_empty_annotation_and_legend_witness_is_already_closed_without_reprepare(monkeypatch):
    layout = MeasuredLegend((), Decimal(0), (), Decimal(100), Decimal(100))
    initial = _initial_plan((), layout)
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda *args, **kwargs: pytest.fail("empty exact witness should not reprepare"))
    observed = CompletedSourceUse((), layout, ())

    plan, composition = closure.complete_source_render_plan(
        _value(), lambda value, plan: _Composition(observed), initial=initial)

    assert plan is initial
    assert composition.source_use == observed


def test_unrelated_composition_error_propagates_unchanged(monkeypatch):
    monkeypatch.setattr(closure, "prepare_surface_render_plan",
                        lambda value, *, source_use=None, activate_annotations=False:
                        SimpleNamespace(activated=activate_annotations))
    failure = LayoutError("E_LAYOUT_CONFIGURATION", "/profile")

    with pytest.raises(LayoutError) as caught:
        closure.complete_source_render_plan(_value(),
            lambda value, plan: (_ for _ in ()).throw(failure))

    assert caught.value is failure
