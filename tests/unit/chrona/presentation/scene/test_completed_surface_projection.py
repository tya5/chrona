"""Scene receives completed placements and cannot replay Layout."""
import ast
import inspect

from chrona.presentation import surface_pipeline
from chrona.presentation.layout import surface_composer
from chrona.presentation.scene import v05_builder
from tests.support import synthetic_review as sr


def test_scene_projection_replays_no_layout_or_measurement(tmp_path, monkeypatch):
    inputs, calls = [], []
    project = surface_pipeline.project_review_surface
    compose = surface_pipeline.compose_surface_layout

    def capture(value):
        inputs.append(value)
        return project(value)

    def counted(*args, **kwargs):
        calls.append(None)
        return compose(*args, **kwargs)

    monkeypatch.setattr(surface_pipeline, "project_review_surface", capture)
    monkeypatch.setattr(surface_pipeline, "compose_surface_layout", counted)
    rendered = sr.render(tmp_path, sr.chain_project(groups=1, per_group=2))
    assert len(inputs) == len(calls) == 1
    value = inputs[0]
    assert not {"font_metrics", "measured_sources", "surface_preparation",
                "fixed_lane_preflight", "progress"} & value.__dict__.keys()

    def forbidden(*args, **kwargs):
        raise AssertionError("Scene must only project the accepted Layout result")

    monkeypatch.setattr(surface_pipeline, "compose_surface_layout", forbidden)
    monkeypatch.setattr(surface_composer, "compose_surface_layout", forbidden)
    assert project(value) == rendered.surface


def test_scene_has_no_layout_composition_or_measurement_request_construction():
    tree = ast.parse(inspect.getsource(v05_builder))
    forbidden = {"compose_surface_layout", "compose_dependency_network_surface",
                 "SurfaceLayoutRequest", "measure_sources", "prepare_surface_content"}
    calls = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls & forbidden
