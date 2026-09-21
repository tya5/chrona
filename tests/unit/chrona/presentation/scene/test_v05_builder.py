from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutDecision, LayoutManifest, Rect
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.scene.v05_builder import SceneBuildError, build_scene_input


def _manifest(*sources):
    rect = Rect(Decimal(0), Decimal(0), Decimal(1), Decimal(1))
    return LayoutManifest("review", "sha256:test", "horizontal-tb", rect,
                          tuple(LayoutDecision(source, "slot", rect, source) for source in sources))


def _theme():
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"ink": {"type": "color", "value": "#102030"},
                   "body": {"type": "fontFamily", "value": "Test Sans"}},
        "roles": {"text": {"fill": "ink", "fontFamily": "body"}}, "metrics": {}}}


def _measurements():
    return MeasuredSources({}, {}, {"text.body.size": Decimal(14)})


def test_scene_input_accepts_only_completed_current_runtime_boundaries():
    value = build_scene_input(projection={"window": (date(2026, 1, 1), date(2026, 1, 2))},
                              surface_content=SurfaceContentInput(),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=object(), measured_sources=_measurements(),
                              capabilities={"svg": True})
    assert value.theme_tokens.color("text") == "#102030"


def test_scene_input_rejects_a_layout_without_a_required_source():
    with pytest.raises(SceneBuildError, match="E_PRESENTATION_PRIMITIVE_MISSING") as error:
        build_scene_input(projection={}, surface_content=SurfaceContentInput(),
                          layout_manifest=_manifest("title", "table", "timeline"),
                          resolved_theme=_theme(), font_metrics=object(), measured_sources=_measurements(),
                          capabilities={"svg": True})
    assert error.value.path == "/layoutManifest/sources/timeline-axis"


def test_scene_input_requires_frozen_source_measurements():
    with pytest.raises(SceneBuildError, match="E_PRESENTATION_MEASUREMENTS_REQUIRED"):
        build_scene_input(projection={}, surface_content=SurfaceContentInput(),
                          layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                          resolved_theme=_theme(), font_metrics=object(), measured_sources={}, capabilities={"svg": True})
