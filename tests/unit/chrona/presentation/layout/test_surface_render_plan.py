"""Preparation ownership, pure replay and original font-error precedence."""
import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
import inspect

import pytest

from chrona.presentation.layout import surface_render_plan as planner
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.font_metrics import FontMetricsError
from chrona.usecases import render_review as usecase
from tests.support import synthetic_review as sr


def _capture(tmp_path, monkeypatch):
    inputs, plans = [], []
    original = planner.prepare_surface_render_plan

    def observe(value):
        before = deepcopy((value.profile, value.theme, value.project))
        result = original(value)
        assert (value.profile, value.theme, value.project) == before
        inputs.append(value)
        plans.append(result)
        return result

    monkeypatch.setattr(usecase, "prepare_surface_render_plan", observe)
    sr.render(tmp_path, sr.chain_project(groups=1, per_group=2))
    assert len(inputs) == len(plans) == 1
    return inputs[0], plans[0]


def test_preparation_replay_has_identical_manifest_and_fresh_request_state(tmp_path, monkeypatch):
    value, first = _capture(tmp_path, monkeypatch)
    second = planner.prepare_surface_render_plan(value)
    assert first.manifest.canonical_bytes() == second.manifest.canonical_bytes()
    assert first.viewport == second.viewport
    assert first.content == second.content
    assert first.preparation.inline.request is not second.preparation.inline.request
    assert first.preparation.inline.request.mark_visibility_index is not (
        second.preparation.inline.request.mark_visibility_index)
    with pytest.raises(FrozenInstanceError):
        first.viewport = (1, 1)


def test_source_font_failure_still_precedes_invalid_layout_profile(tmp_path, monkeypatch):
    value, _ = _capture(tmp_path, monkeypatch)
    profile_error = LayoutError("E_LAYOUT_SCHEMA", "/root")
    font_error = FontMetricsError("E_FONT_METRICS_INVALID", "/font")

    def invalid_profile(*args, **kwargs):
        raise profile_error

    def invalid_sources(*args, **kwargs):
        raise font_error

    monkeypatch.setattr(planner, "resolve_layout_profile", invalid_profile)
    monkeypatch.setattr(planner, "measure_sources", invalid_sources)
    with pytest.raises(planner.SurfacePlanFontError) as caught:
        planner.prepare_surface_render_plan(value)
    assert caught.value.failure is font_error


def test_application_has_no_measurement_allocation_or_candidate_callbacks():
    tree = ast.parse(inspect.getsource(usecase))
    forbidden = {"measure_sources", "measure_natural_normal_flow_block",
                 "resolve_content_block_extent", "solve_layout", "SourceSizingSession",
                 "prepare_surface_natural_candidate", "reserve_slot_heading_blocks"}
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls & forbidden
    assert "candidate_request" not in {node.name for node in ast.walk(tree)
                                       if isinstance(node, ast.FunctionDef)}
