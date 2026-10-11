"""Real label request/completion tests for temporal, non-spatial absence."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.model.info_diagnostics import SuppressedPlotLabels
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.projection import WindowMode
from tests.unit.chrona.presentation.layout.test_surface_window_marks import _compose
from tests.unit.chrona.presentation.layout.test_lane_item_footprints import _window_footprint_fixture
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request
from chrona.presentation.layout.lane_label_intent import measure_lane_member_labels
from chrona.presentation.layout.surface_mark_visibility import build_item_mark_visibility_index
from tests.unit.chrona.presentation.layout.test_label_visual_measurement import _icon


def _request(*, content=("title", "finishDelta"), containing=False, mode=WindowMode.EXPLICIT):
    window = (date(2026, 1, 1), date(2026, 1, 15)) if containing else (
        date(2026, 1, 5), date(2026, 1, 9))
    base, _ = _compose(window=window, mode=mode)
    projection = replace(base.request.projection,
        items=tuple(replace(item, finish_delta=4) for item in base.request.projection.items))
    surface_content = replace(base.request.surface_content, show_member_labels=True,
                              label_placement="plot", label_content=content,
                              label_side="inside", label_overflow="suppress")
    return replace(base.request, projection=projection, surface_content=surface_content,
                   presentation_contract=normalize_presentation_input(surface_content),
                   mark_visibility_index=None)


def test_outside_names_are_non_spatial_absences_and_title_intent_loses_only_outside_delta():
    placement = compose_surface_layout(_request()).placement
    assert {item.source_ref for item in placement.window_label_absences} == {"before", "after"}
    assert all(item.semantic_id == "memberLabel" for item in placement.window_label_absences)
    labels = tuple(item for item in placement.text if item.semantic_id == "memberLabel")
    assert len(labels) == 1 and labels[0].content == "across"
    assert all(item.source_ref not in {"before", "after"} for item in labels)
    spatial = sum(item.overflow == "suppressed" for item in labels)
    assert placement.info_diagnostics == (SuppressedPlotLabels("table-timeline", 2 + spatial),)
    assert placement.lane_label_suppressions == ()
    assert all(absence.diagnostic in placement.diagnostics for absence in placement.window_label_absences)
    assert all(not hasattr(absence, "bounds") for absence in placement.window_label_absences)
    placement.assert_valid()


def test_delta_only_outside_labels_are_absences_without_measured_text_or_fake_anchor():
    placement = compose_surface_layout(_request(content=("finishDelta",))).placement
    assert {item.source_ref for item in placement.window_label_absences} == {"before", "across", "after"}
    assert not any(item.semantic_id == "memberLabel" for item in placement.text)
    assert placement.info_diagnostics == (SuppressedPlotLabels("table-timeline", 3),)


def test_containing_explicit_window_keeps_derived_label_geometry_and_intent():
    explicit = compose_surface_layout(_request(containing=True)).placement
    derived = compose_surface_layout(_request(containing=True, mode=WindowMode.SELECTED_PLANNED)).placement
    assert explicit == derived
    assert explicit.window_label_absences == ()


def test_standalone_delta_absences_do_not_enlarge_member_name_count():
    request = _request(content=("title",))
    request = replace(request, projection=replace(request.projection,
        items=tuple(replace(item, source_kind="combined") for item in request.projection.items)))
    placement = compose_surface_layout(request).placement
    deltas = tuple(item for item in placement.window_label_absences if item.semantic_id == "finishDelta")
    assert {item.source_ref for item in deltas} == {"before", "across", "after"}
    members = sum(item.semantic_id == "memberLabel" for item in placement.window_label_absences)
    spatial = sum(item.semantic_id == "memberLabel" and item.overflow == "suppressed"
                  for item in placement.text)
    assert placement.info_diagnostics == (SuppressedPlotLabels("table-timeline", members + spatial),)


def test_attached_label_on_outside_host_has_no_spatial_overflow_fallback():
    request = _request()
    request = replace(request, surface_content=replace(request.surface_content,
        attached_labels=(("before", "Attached name"),)),
        projection=replace(request.projection, items=tuple(
            replace(item, attached_to="across") if item.object_id == "before" else item
            for item in request.projection.items)))
    placement = compose_surface_layout(request).placement
    absence = next(item for item in placement.window_label_absences if item.source_ref == "before")
    assert absence.components == (("attached", "Attached name"),)
    assert not any(item.source_ref == "before" and item.semantic_id == "memberLabel"
                   for item in placement.text)


@pytest.mark.parametrize("selector", [(("id", "before"),), (("placementId", "member-label:before"),)])
def test_visual_on_proven_outside_label_is_unpainted_not_an_invalid_target(selector):
    request = _request()
    visual = VisualRequest("plot-label", selector, ref="icon", source_ref="/body/visuals/0")
    request = replace(request, visual_requests=(visual,), icon_assets={"icon": _icon()})
    placement = compose_surface_layout(request).placement
    assert not any(icon.visual_capability_source_ref == visual.source_ref for icon in placement.icons)
    assert any(absence.source_ref == "before" for absence in placement.window_label_absences)


@pytest.mark.parametrize("failure,code", [("missing-icon", "E_ICON_NAME_UNKNOWN"),
    ("duplicate", "E_LAYOUT_VISUAL_DUPLICATE"), ("invalid-target", "E_LAYOUT_VISUAL_TARGET")])
def test_omission_does_not_hide_invalid_visual_bindings(failure, code):
    request = _request()
    target = "not-a-label" if failure == "invalid-target" else "before"
    visual = VisualRequest("plot-label", (("id", target),), ref="icon", source_ref="/body/visuals/0")
    visuals = (visual, replace(visual, source_ref="/body/visuals/1")) if failure == "duplicate" else (visual,)
    request = replace(request, visual_requests=visuals,
                      icon_assets={} if failure == "missing-icon" else {"icon": _icon()})
    with pytest.raises(LayoutError, match=code):
        compose_surface_layout(request)


def test_lane_measurement_uses_the_shared_admission_before_measuring_text():
    projection, _, _ = _window_footprint_fixture()
    across = replace(projection.items[1], planned={
        "start": date(2026, 1, 1), "end": date(2026, 1, 9)}, finish_delta=4)
    items = (projection.items[0], across, projection.items[2])
    projection = replace(projection, items=items,
        rows=tuple(replace(row, items=(item,)) for row, item in zip(projection.rows, items)),
        lane_rows=(replace(projection.lane_rows[0], items=items),))
    request = _axis_request(())
    content = replace(request.surface_content, show_member_labels=True,
        label_content=("title", "finishDelta"), label_placement="plot")
    measured = measure_lane_member_labels(projection, content, timeline_inline_size=200,
        theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
        visual_requests=(), icon_assets={},
        mark_visibility_index=build_item_mark_visibility_index(projection, as_of=content.as_of))
    assert len(measured) == 1 and measured[0].source_ref == across.object_id
    assert measured[0].content == across.title


@pytest.mark.parametrize("failure", ["duplicate", "missing-warning", "wrong-count", "also-text"])
def test_temporal_label_counts_and_exclusive_emission_are_strict(failure):
    placement = compose_surface_layout(_request()).placement
    absence = placement.window_label_absences[0]
    if failure == "duplicate":
        invalid = replace(placement, window_label_absences=(*placement.window_label_absences, absence))
    elif failure == "missing-warning":
        invalid = replace(placement, diagnostics=tuple(item for item in placement.diagnostics
                                                       if item != absence.diagnostic))
    elif failure == "wrong-count":
        invalid = replace(placement, info_diagnostics=(SuppressedPlotLabels("table-timeline", 1),))
    else:
        extra = TextPlacement(absence.placement_id, absence.source_ref, "not admitted", Rect(0, 0, 1, 1),
                              "text", required=False, semantic_id="memberLabel")
        invalid = replace(placement, text=(*placement.text, extra))
    with pytest.raises(ValueError, match="E_LAYOUT_SUPPRESSION_COUNT_INVALID"):
        invalid.assert_valid()


@pytest.mark.parametrize("failure", ["borrowed", "unproved", "wrong-source", "wrong-identity"])
def test_temporal_absence_cannot_forge_or_borrow_a_source_admission(failure):
    absence = compose_surface_layout(_request()).placement.window_label_absences[0]
    changes = {"admission": replace(absence.admission)} if failure == "borrowed" else (
        {"visibility_index": None} if failure == "unproved" else
        {"placement_id": "member-label:another-object"} if failure == "wrong-identity" else
        {"source_ref": "another-object"})
    with pytest.raises(LayoutError, match="E_LAYOUT_WINDOW_CLIP"):
        replace(absence, **changes)
