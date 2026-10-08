"""Candidate-specific Layout demand stays bound to each native manifest."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from importlib import import_module

import pytest

from chrona.presentation.layout.surface_composer import (
    prepare_surface_content as native_prepare_surface_content,
    prepare_surface_natural_candidate as native_prepare_surface_natural_candidate,
)
from tests.support import synthetic_review as sr


@pytest.mark.parametrize(("block_size", "draft_auto"), [(80, False), (None, True)])
def test_lane_render_uses_each_candidate_manifest_and_reuses_final_natural_geometry(
        tmp_path, monkeypatch, block_size, draft_auto):
    usecase = import_module("chrona.usecases.render_review")
    natural_calls = []
    demand_calls = []
    final_completions = []
    resolutions = []

    def prepare_natural(request):
        natural = native_prepare_surface_natural_candidate(request)
        natural_calls.append((request, natural))
        return natural

    def prepare_content(request, *, natural=None):
        final_completions.append((request, natural))
        return native_prepare_surface_content(request, natural=natural)

    native_resolve = usecase.resolve_content_block_extent

    def resolve_with_demand_trace(*args, **kwargs):
        demand = kwargs["required_blocks"]

        def traced_demand(manifest):
            before = len(natural_calls)
            result = demand(manifest)
            assert len(natural_calls) == before + 1
            request, natural = natural_calls[-1]
            demand_calls.append((manifest, request, natural, result))
            return result

        kwargs["required_blocks"] = traced_demand
        result = native_resolve(*args, **kwargs)
        resolutions.append(result)
        return result

    monkeypatch.setattr(usecase, "prepare_surface_natural_candidate", prepare_natural)
    monkeypatch.setattr(usecase, "prepare_surface_content", prepare_content)
    monkeypatch.setattr(usecase, "resolve_content_block_extent", resolve_with_demand_trace)

    directory = tmp_path / ("auto" if draft_auto else "finite")
    directory.mkdir()
    parts = sr.bundle("executive-light")
    parts["view"] = sr.lane_view(parts["view"])
    source = sr.project({
        "a": sr.span("a", date(2026, 1, 5), 20, owner="a"),
        "b": sr.span("b", date(2026, 1, 5), 20, owner="b"),
    })
    rendered = sr.render(directory, source, presentation=parts, viewport=(1600, block_size))

    assert demand_calls and len(resolutions) == 1 and len(final_completions) == 1
    assert len(natural_calls) == len(demand_calls) + 1
    for manifest, request, natural, required in demand_calls:
        assert request.layout_manifest is manifest
        assert natural.inline.request.layout_manifest is manifest
        assert natural.inline.request.surface_content is request.surface_content
        assert natural.inline.request.fixed_lane_preflight is not None
        source = next(item for item in manifest.decisions if item.source == "timeline")
        assert natural.inline.request.fixed_lane_preflight.seed_inline_frame.timeline_inline_size == (
            source.bounds.inline_size)
        assert required["timeline"] == natural.required_timeline_block()

    final_request, final_natural = natural_calls[-1]
    completed_request, completed_natural = final_completions[-1]
    assert completed_request is final_natural.inline.request
    assert completed_natural is final_natural
    assert final_request.layout_manifest is final_natural.inline.request.layout_manifest
    assert final_request.layout_manifest is completed_request.layout_manifest
    assert final_natural.inline.request.fixed_lane_preflight is not None
    assert final_natural.inline.request.fixed_lane_preflight is not final_request.fixed_lane_preflight

    timeline = next(slot for slot in rendered.surface.slots if slot.slot_id == "timeline")
    final_timeline = next(item for item in final_request.layout_manifest.decisions if item.source == "timeline")
    assert final_natural.inline.request.fixed_lane_preflight.seed_inline_frame.timeline_inline_size == (
        final_timeline.bounds.inline_size)
    assert (Decimal(str(timeline.bounds[0])), Decimal(str(timeline.bounds[1])),
            Decimal(str(timeline.bounds[2])), Decimal(str(timeline.bounds[3]))) == (
        final_timeline.bounds.inline, final_timeline.bounds.block,
        final_timeline.bounds.inline_size, final_timeline.bounds.block_size)
    if not draft_auto:
        assert final_request.layout_manifest.viewport.block_size > Decimal(block_size)
