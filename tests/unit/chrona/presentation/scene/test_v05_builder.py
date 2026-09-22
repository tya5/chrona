from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from chrona.presentation.layout.model import LayoutDecision, LayoutManifest, Measurement, Rect
from chrona.presentation.layout.sources import MeasuredSources, SourceInput
from chrona.presentation.model.surface_content import SummaryContent, SurfaceContentInput
from chrona.presentation.model.projection import ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.scene.v05_builder import SceneBuildError, build_scene_input, compose_review_surface


def surface_content(table_columns=(), table_cells=(), **overrides):
    value = dict(
        table_columns=table_columns, table_cells=table_cells, relations=(), annotations=(),
        show_member_labels=False, label_placement="none", label_content=(), label_side="auto",
        label_overflow="diagnose", relation_overflow="diagnose", group_presentation="band",
        axis_level="auto", axis_levels=(), axis_ticks=None, as_of=None, as_of_label="As of",
        annotation_numbered=False, calendar_closed=(), notes=(), legend_entries=(), coverage_text="",
        summary=SummaryContent(()), template_values=(), group_details=(),
        milestones=(), observation_columns=(), observation_rows=(),
    )
    value.update(overrides)
    return SurfaceContentInput(**value)


def test_scene_delegates_common_surface_geometry_to_layout_composer():
    source = Path(__import__("chrona.presentation.scene.v05_builder", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    assert "compose_surface_layout(" in source
    assert "place_rows(" not in source
    assert "place_mark_tracks(" not in source


def test_scene_projects_completed_layout_geometry_without_measurement_or_routing_imports():
    source = Path(__import__("chrona.presentation.scene.v05_builder", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    forbidden = (
        "from chrona.presentation.layout.text import",
        "from chrona.presentation.layout.routing import",
        "from chrona.presentation.layout.annotations import",
        "place_relation_route(",
        "route_annotation_leader(",
        "measure_text_width(",
        "place_text(",
    )
    assert all(fragment not in source for fragment in forbidden)


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


def _title_measurement():
    return Measurement(Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(1), Decimal(18), Decimal(18))


def test_scene_input_accepts_only_completed_current_runtime_boundaries():
    value = build_scene_input(projection={"window": (date(2026, 1, 1), date(2026, 1, 2))},
                              surface_content=surface_content(),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=object(), measured_sources=_measurements(),
                              capabilities={"svg": True})
    assert value.theme_tokens.color("text") == "#102030"


def test_scene_input_rejects_a_layout_without_a_required_source():
    with pytest.raises(SceneBuildError, match="E_PRESENTATION_PRIMITIVE_MISSING") as error:
        build_scene_input(projection={}, surface_content=surface_content(),
                          layout_manifest=_manifest("title", "table", "timeline"),
                          resolved_theme=_theme(), font_metrics=object(), measured_sources=_measurements(),
                          capabilities={"svg": True})
    assert error.value.path == "/layoutManifest/sources/timeline-axis"


def test_scene_input_requires_frozen_source_measurements():
    with pytest.raises(SceneBuildError, match="E_PRESENTATION_MEASUREMENTS_REQUIRED"):
        build_scene_input(projection={}, surface_content=surface_content(),
                          layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                          resolved_theme=_theme(), font_metrics=object(), measured_sources={}, capabilities={"svg": True})


class _Font:
    content_identity = "sha256:test"
    def width(self, value, size): return len(value) * size / 2


def test_core_surface_uses_frozen_slots_measurements_and_normalized_cells():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 2, 1)}, None, None, ("planned",)),),
                                  (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"), "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    manifest = _manifest("title", "table", "timeline", "timeline-axis")
    value = build_scene_input(projection=projection, surface_content=surface_content((("name", "Name"),), (("a", "name", "A"),)),
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
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"), "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
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
    value = build_scene_input(projection=projection, surface_content=surface_content(
        relations=({"id": "r", "from": {"object": "a"}, "to": {"object": "b"}},),
        annotations=({"id": "note", "purpose": "callout", "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "finish"},
                      "placement": {"side": "end", "alignment": "center"}, "text": "Check"},)),
        layout_manifest=manifest, resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    dependency = next(item for item in surface.primitives if item.scene_id == "relation:r")
    leader = next(item for item in surface.primitives if item.scene_id == "annotation-leader:note")
    assert dependency.shape == "triangle"
    assert dependency.purpose == "dependency"
    assert dependency.points[0][0] == 500
    assert dependency.points[-1][0] == 100
    assert next(item for item in surface.primitives if item.scene_id == "planned:a").purpose == "planned"
    assert leader.from_port_id == "a:planned:finish"
    assert leader.to_port_id == "annotation-box:note"


def test_explicit_row_members_keep_fixed_mark_size_labels_and_snapshot_role():
    primary = ReviewItem("a", "Current plan", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, (), item_id="primary", source_kind="primary")
    snapshot = ReviewItem("a", "Baseline", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 8)}, None, None, (), item_id="snapshot", source_kind="snapshot")
    row = ReviewRowProjection("release", "Release", "", "primary", (primary, snapshot))
    projection = ReviewProjection((primary,), (date(2026, 1, 1), date(2026, 1, 10)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(show_member_labels=True),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    planned = next(item for item in surface.primitives if item.scene_id == "planned:release:primary")
    baseline = next(item for item in surface.primitives if item.scene_id == "planned:release:snapshot")
    assert planned.bounds[3] == baseline.bounds[3] == 8
    assert baseline.visual_role == "snapshot"
    assert any(item.scene_id == "member-label:release:primary" and item.text == "Current plan"
               for item in surface.primitives)


def test_scene_projects_only_accepted_typed_plot_labels_and_relations():
    projection = ReviewProjection((
        ReviewItem("a", "A very long label", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, ()),
        ReviewItem("b", "B", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 9)}, None, None, ()),
    ), (date(2026, 1, 1), date(2026, 1, 10)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    rect = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(1000))
    manifest = LayoutManifest("review", "sha256:test", "horizontal-tb", rect,
                              tuple(LayoutDecision(source, "slot", rect, source)
                                    for source in ("title", "table", "timeline", "timeline-axis")),
                              relation_max_bends=0)
    value = build_scene_input(
        projection=projection,
        surface_content=surface_content(
            relations=({"id": "depends", "from": {"object": "a"}, "to": {"object": "b"}},),
            label_placement="plot", label_content=("title",), label_side="auto", label_overflow="suppress",
            relation_overflow="suppress",
        ),
        layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
        capabilities={"svg": True},
    )
    surface = compose_review_surface(value)
    assert not any(item.scene_id == "member-label:a" for item in surface.primitives)
    assert not any(item.scene_id.startswith("relation:depends") for item in surface.primitives)


def test_same_explicit_row_relation_uses_distinct_mark_ports():
    first = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 4)}, None, None, (), item_id="a", source_kind="primary")
    second = ReviewItem("b", "B", "span", {"start": date(2026, 1, 5), "end": date(2026, 1, 9)}, None, None, (), item_id="b", source_kind="primary")
    row = ReviewRowProjection("phase", "Phase", "", "a", (first, second))
    projection = ReviewProjection((first, second), (date(2026, 1, 1), date(2026, 1, 9)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    theme = _theme()
    theme["body"]["values"]["marker"] = {"type": "marker", "value": "triangle"}
    theme["body"]["roles"]["dependency"] = {"marker": "marker"}
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(relations=({"id": "depends", "from": {"object": "a"}, "to": {"object": "b"}},)),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    relation = next(item for item in surface.primitives if item.scene_id == "relation:depends:phase:a:phase:b")
    assert len(relation.points) >= 2
    assert relation.points[0] != relation.points[-1]


def test_legend_entries_emit_role_derived_swatches():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(legend_entries=(("planned", "Plan"),)),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis", "legend"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    swatch = next(node for node in surface.primitives if node.scene_id == "legend-swatch:planned")
    assert swatch.kind == "Rect"
    assert swatch.visual_role == "planned"


def test_shared_track_overlays_snapshot_planned_and_actual_in_stable_order():
    snapshot = ReviewItem("a", "Baseline", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, (), item_id="snapshot", source_kind="snapshot", track="shared")
    primary = ReviewItem("a", "Plan", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 7)}, {"start": date(2026, 1, 3), "finish": date(2026, 1, 8)}, None, (), item_id="planned", source_kind="primary", track="shared")
    actual = ReviewItem("a", "Actual", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 7)}, {"start": date(2026, 1, 3), "finish": date(2026, 1, 8)}, None, (), item_id="actual", source_kind="actual", track="shared")
    row = ReviewRowProjection("release", "Release", "", "planned", (actual, primary, snapshot))
    projection = ReviewProjection((primary,), (date(2026, 1, 1), date(2026, 1, 8)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection, surface_content=surface_content(),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)
    marks = [node for node in surface.primitives if node.scene_id in {"planned:release:snapshot", "planned:release:planned", "actual:release:actual"}]

    assert [node.scene_id for node in marks] == ["planned:release:snapshot", "planned:release:planned", "actual:release:actual"]
    assert len({node.bounds[1] for node in marks}) == 1


def test_grouped_rows_reserve_and_emit_a_group_header():
    item = ReviewItem("a", "Firmware", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 4)}, None, None, (),
                      group_id="fw", group_label="Firmware team", item_id="a")
    row = ReviewRowProjection("fw-row", "Firmware", "fw", "a", (item,))
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 4)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8),
                                   "timeline.groupHeader.blockSize": Decimal(20)})
    value = build_scene_input(projection=projection, surface_content=surface_content(group_presentation="header"),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    assert any(node.scene_id == "group-header:fw" and node.text == "Firmware team"
               for node in surface.primitives)
    assert surface.groups[0].header_bounds is not None


def test_declared_actual_cutoff_emits_as_of_marker_only_within_window():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 10)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(as_of=date(2026, 1, 5)),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    assert next(node for node in surface.primitives if node.scene_id == "as-of").visual_role == "as-of"
    assert any(node.scene_id == "as-of-label" for node in surface.primitives)


def test_project_calendar_closure_emits_background_shading():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(calendar_closed=(date(2026, 1, 3),)),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    assert next(node for node in surface.primitives if node.scene_id == "calendar-closed:2026-01-03").visual_role == "calendar-closed"


def test_month_axis_emits_quarter_band_labels():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2027, 1, 1)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2027, 1, 1)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection, surface_content=surface_content(),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    assert any(node.scene_id.startswith("axis-band:quarter:") for node in surface.primitives)


def test_table_columns_use_measured_non_overlapping_origins():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content((("long", "Long heading"), ("short", "B")),
                                                                (("a", "long", "a deliberately long table value"), ("a", "short", "B"))),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)
    assert next(item for item in surface.primitives if item.scene_id == "column:short").bounds[0] > next(item for item in surface.primitives if item.scene_id == "column:long").bounds[0]
