from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutDecision, LayoutManifest, Rect
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.scene.v05_builder import SceneBuildError, build_scene_input, compose_review_surface


def _manifest(*sources):
    rect = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(1000))
    return LayoutManifest("review", "sha256:test", "horizontal-tb", rect,
                          tuple(LayoutDecision(source, "slot", rect, source) for source in sources))


def _theme():
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"ink": {"type": "color", "value": "#102030"},
                   "body": {"type": "fontFamily", "value": "Test Sans"},
                   "regular": {"type": "fontWeight", "value": 400},
                   "body-size": {"type": "number", "value": 14},
                   "heading-size": {"type": "number", "value": 24},
                   "axis-size": {"type": "number", "value": 12},
                   "line": {"type": "number", "value": "1.4"}},
        "roles": {**{name: {"fontFamily": "body", "fontWeight": "regular", "fontSize": size, "lineHeight": "line"}
                     for name, size in {"text": "body-size", "heading": "heading-size", "axis": "axis-size", "legend": "axis-size", "summary": "body-size", "annotation": "body-size"}.items()},
                  "text": {"fill": "ink", "fontFamily": "body", "fontWeight": "regular", "fontSize": "body-size", "lineHeight": "line"}}, "metrics": {}}}


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


class _Font:
    content_identity = "sha256:test"
    def width(self, value, size): return len(value) * size / 2


def test_core_surface_uses_frozen_slots_measurements_and_normalized_cells():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 2, 1)}, None, None, ("planned",)),),
                                  (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    measurement = MeasuredSources({}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"), "timeline.row.minBlockSize": Decimal(40)})
    manifest = _manifest("title", "table", "timeline", "timeline-axis")
    value = build_scene_input(projection=projection, surface_content=SurfaceContentInput((("name", "Name"),), (("a", "name", "A"),)),
                              layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    assert surface.scale_manifest.domain_start == date(2026, 1, 1)
    assert any(item.scene_id == "cell:a:name" and item.text == "A" for item in surface.primitives)
    assert any(item.scene_id == "planned:a" for item in surface.primitives)
    assert any(item.scene_id == "missing-actual:a" for item in surface.primitives)
    assert next(item for item in surface.primitives if item.scene_id == "title").text_layout.font_size == 24


def test_scene_uses_declared_marker_and_projects_an_object_annotation_leader():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 11)}, None, None, ("planned",)),
                                  ReviewItem("b", "B", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 6)}, None, None, ("planned",))),
                                  (date(2026, 1, 1), date(2026, 1, 11)), (), ())
    measurement = MeasuredSources({}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"), "timeline.row.minBlockSize": Decimal(40)})
    viewport = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(300))
    manifest = LayoutManifest("review", "sha256:test", "horizontal-tb", viewport, (
        LayoutDecision("title", "slot", Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(40)), "title"),
        LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(40), Decimal(100), Decimal(100)), "table"),
        LayoutDecision("timeline", "slot", Rect(Decimal(100), Decimal(40), Decimal(400), Decimal(100)), "timeline"),
        LayoutDecision("axis", "slot", Rect(Decimal(100), Decimal(140), Decimal(400), Decimal(40)), "timeline-axis"),
        LayoutDecision("annotations", "slot", Rect(Decimal(500), Decimal(40), Decimal(300), Decimal(100)), "annotations", priority="required", overflow="diagnose"),
    ))
    theme = _theme()
    theme["body"]["values"].update({"marker": {"type": "marker", "value": "triangle"}})
    theme["body"]["roles"]["dependency"] = {"marker": "marker"}
    value = build_scene_input(projection=projection, surface_content=SurfaceContentInput(
        relations=({"id": "r", "from": {"object": "a"}, "to": {"object": "b"}},),
        annotations=({"id": "note", "purpose": "callout", "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "finish"},
                      "placement": {"side": "end", "alignment": "center"}, "text": "Check"},)),
        layout_manifest=manifest, resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    dependency = next(item for item in surface.primitives if item.scene_id == "relation:r")
    leader = next(item for item in surface.primitives if item.scene_id == "annotation-leader:note")
    assert dependency.shape == "triangle"
    assert leader.from_port_id == "a:planned:finish"
    assert leader.to_port_id == "annotation-box:note"
