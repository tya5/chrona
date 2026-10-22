"""Measured member groups can change pose without repeating font work."""
from dataclasses import replace

import pytest

from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.surface_member_label_measurement import (
    prepare_member_label_candidate, project_prepared_member_text,
)
from chrona.presentation.layout.text import place_text
from tests.unit.chrona.presentation.layout.test_member_label_required_phase import (
    _placement_context, _request,
)


@pytest.mark.parametrize("inline,baseline", [(17.125, 37.3), (0, 10), (1523.615090909091, 874.75)])
def test_projection_retains_exact_native_bounds_and_typography_without_remeasurement(inline, baseline):
    context = _placement_context()
    request = replace(_request("name"), content="Mixed title", estimated_delta=True)
    prepared = prepare_member_label_candidate(request, role="text", measured_lane_label=None,
        request=context.request, timeline_rect=LabelRect(*context.timeline_bounds),
        slot=context.by_source["timeline"], host=None, associated_member=False,
        own_marks=(), member_names={}, as_of_chip_measurement=None)
    expected = place_text(placement_id=request.placement_id, source_ref=request.source_ref,
        content=request.content, inline=inline, baseline_block=baseline,
        typography_role="text", theme_tokens=context.request.theme_tokens,
        font_metrics=context.request.font_metrics, collision_region=request.collision_region,
        collision_domain=request.collision_domain, semantic_id=request.semantic_id,
        lines=prepared.measurement.lines, estimated_delta=True, overflow="visible-overflow")

    def no_more_measurement(*_args, **_kwargs):
        pytest.fail("a completed measured candidate must not measure again")

    context.request.font_metrics.width = no_more_measurement
    context.request.theme_tokens.text_treatment = no_more_measurement
    actual = project_prepared_member_text(prepared, inline=inline,
        baseline_block=baseline, overflow="visible-overflow")
    assert actual == expected
    assert prepared.provisional.baseline == (0, 10)
