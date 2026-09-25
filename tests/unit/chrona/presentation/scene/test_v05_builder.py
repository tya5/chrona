from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import LayoutDecision, LayoutManifest, Measurement, Rect
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_quality import PathCommand, SurfaceLayoutRequest
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun, SourceInput
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.surface_content import AnnotationIntent, AxisLabelIntent, AxisTier, SummaryContent, SurfaceContentInput, TableCellContent, TableColumnContent, TableColumnWidth
from chrona.presentation.model.surface_content import RelationPresentationFact
from chrona.presentation.model.projection import FoldedPointProjection, ReviewItem, ReviewProjection, ReviewRowProjection
from chrona.presentation.model.semantic_registry import semantic_binding, semantic_ids
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface, SymbolGeometry, TextLayout
from chrona.presentation.scene.v05_builder import SceneBuildError, build_scene_input, compose_review_surface

BACKGROUND_EXTENTS = {"rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"}


def surface_content(table_columns=(), table_cells=(), **overrides):
    table_columns = tuple(
        item if isinstance(item, TableColumnContent) else TableColumnContent(item[0], item[1], "start", TableColumnWidth("content", "content"))
        for item in table_columns
    )
    table_cells = tuple(item if isinstance(item, TableCellContent) else TableCellContent(*item, "tableCell")
                        for item in table_cells)
    value = dict(
        table_columns=table_columns, table_cells=table_cells, relations=(), annotations=(),
        show_member_labels=False, label_placement="none", label_content=(), label_side="auto",
        label_overflow="visible-overflow", relation_overflow="visible-overflow", group_presentation="band",
        axis_tiers=(), axis_fiscal_start_month=1, as_of=None, as_of_label="As of",
        annotation_numbered=False, calendar_closed=(), calendar_exceptions=(), notes=(), legend_entries=(), coverage_text="",
        summary=SummaryContent(()), template_values=(), group_details=(),
        milestones=(), observation_columns=(), observation_rows=(),
    )
    value.update(overrides)
    value["annotations"] = tuple(
        item if isinstance(item, AnnotationIntent) else AnnotationIntent(
            item["id"], item["purpose"], dict(item["anchor"]), item["placement"]["side"],
            item["placement"].get("alignment", "center"), item["text"], item.get("number"))
        for item in value["annotations"]
    )
    value["relations"] = tuple(
        item if isinstance(item, RelationPresentationFact) else RelationPresentationFact(
            str(item["id"]), str(item["from"]["object"]), str(item["from"].get("endpoint", "end")),
            str(item["to"]["object"]), str(item["to"].get("endpoint", "start")), item.get("lag", "0d"),
            None, str(item.get("_semantic", "dependency")))
        for item in value["relations"]
    )
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
        "progress_fill_bounds(",
        "placement_id.startswith(\"axis-",
        "annotation_presentation(",
        'semantic_binding("annotation")',
    )
    assert all(fragment not in source for fragment in forbidden)


def test_scene_text_layout_rejects_an_unpaired_orientation_and_rotation() -> None:
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextLayout((0, 0, 1, 1), (0, 0), ("x",), "Test", 400, 12, 1.2,
                   "sha256:test", orientation="rotate-cw", rotation_degrees=-90)


def test_scene_rejects_a_clip_that_does_not_reference_a_preceding_same_slot_host():
    fill = ScenePrimitive("fill", "Rect", "a", "object", "progress-fill", "progress-fill", (0, 0, 1, 1),
                          slot_id="timeline", clip_source_id="host")
    host = ScenePrimitive("host", "Rect", "a", "object", "planned", "planned", (0, 0, 1, 1),
                          slot_id="timeline")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneSurface("s", (), (), (), None, (fill, host))


def test_scene_accepts_a_completed_open_symbol_as_a_clip_host():
    outline = (PathCommand("move", ((0, 0),)), PathCommand("line", ((1, 0),)), PathCommand("line", ((0, 0),)))
    host = ScenePrimitive("host", "Symbol", "a", "object", "actual", "actual", (0, 0, 1, 1),
                          slot_id="timeline", symbol=SymbolGeometry(outline), end_treatment="open")
    fill = ScenePrimitive("fill", "Rect", "a", "object", "progress-fill", "progress-fill", (0, 0, 1, 1),
                          slot_id="timeline", clip_source_id="host")
    SceneSurface("s", (), (), (), None, (host, fill))


def test_scene_roles_are_registry_owned_without_direct_variance_or_scale_role_literals():
    source = Path(__import__("chrona.presentation.scene.v05_builder", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    assert '"variance-ahead"' not in source
    assert '"variance-behind"' not in source
    assert 'role = "planned"' not in source
    assert '"tableCell", href=href' not in source


def _manifest(*sources):
    rect = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(1000))
    bounds = {
        "table": Rect(Decimal(0), Decimal(0), Decimal(500), Decimal(1000)),
        "timeline-axis": Rect(Decimal(500), Decimal(0), Decimal(500), Decimal(48)),
        "timeline": Rect(Decimal(500), Decimal(48), Decimal(500), Decimal(952)),
    }
    return LayoutManifest("review", "sha256:test", "horizontal", "horizontal", rect,
                          tuple(LayoutDecision(source, "slot", bounds.get(source, rect), source) for source in sources),
                          row_distribution="fill", background_extents=BACKGROUND_EXTENTS)


def _theme():
    roles = {semantic_binding(semantic_id).scene_role: {"fill": "ink", "stroke": "ink", "strokeWidth": "stroke-width"}
             for semantic_id in semantic_ids()}
    roles.update({name: {"fill": "ink", "stroke": "ink", "strokeWidth": "stroke-width"}
                  for name in ("background", "variance-ahead", "variance-behind", "variance-on-track", "table-header")})
    for name, size in {"text": "body-size", "heading": "heading-size", "axis": "axis-size", "legend": "axis-size", "summary": "body-size", "annotation": "body-size", "groupHeader": "axis-size",
                       "annotation-callout-text": "body-size", "annotation-highlight-text": "body-size",
                       "annotation-note-text": "body-size", "annotation-arrow-text": "body-size"}.items():
        roles.setdefault(name, {"fill": "ink", "stroke": "ink", "strokeWidth": "stroke-width"}).update(
            {"fontFamily": "body", "fontWeight": "regular", "fontSize": size, "lineHeight": "line",
             "letterSpacing": "letter-spacing", "textTransform": "text-transform",
             "numericSpacing": "numeric-spacing"})
    roles["relationSourceTerminal"] = {"marker": "dependency-marker"}
    roles["relationTargetTerminal"] = {"marker": "dependency-marker"}
    for role, height, offset, order, radius in (
        ("planned", "mark-full", "mark-start", "mark-middle", "mark-square"),
        ("actual", "mark-content", "mark-nested", "mark-front", "mark-rounded"),
        ("snapshot", "mark-full", "mark-start", "mark-back", "mark-square"),
        ("scenario", "mark-full", "mark-start", "mark-back", "mark-square"),
        ("missing-actual", "mark-content", "mark-nested", "mark-front", "mark-rounded"),
    ):
        roles.setdefault(role, {"fill": "ink", "stroke": "ink", "strokeWidth": "stroke-width"}).update(
            {"markHeight": height, "markOffset": offset, "markPaintOrder": order, "markCornerRadius": radius})
    roles["summary-bar"].update({"markHeight": "summary-height"})
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {"ink": {"type": "color", "value": "#102030"},
                   "body": {"type": "fontFamily", "value": "Test Sans"},
                   "regular": {"type": "fontWeight", "value": 400},
                   "body-size": {"type": "number", "value": 14},
                   "heading-size": {"type": "number", "value": 24},
                   "axis-size": {"type": "number", "value": 12},
                   "group-opacity": {"type": "number", "value": "0.12"},
                   "group-header-opacity": {"type": "number", "value": "0.2"},
                   "calendar-opacity": {"type": "number", "value": "0.12"},
                   "stroke-width": {"type": "number", "value": 1},
                   "dependency-marker": {"type": "marker", "value": {"shape": "triangle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}},
                   "milestone-symbol": {"type": "symbol", "value": {"shape": "diamond"}},
                   "line": {"type": "number", "value": "1.4"},
                   "letter-spacing": {"type": "number", "value": 0},
                   "text-transform": {"type": "textTransform", "value": "none"},
                   "numeric-spacing": {"type": "numericSpacing", "value": "proportional"},
                   "mark-full": {"type": "number", "value": 1}, "mark-content": {"type": "number", "value": 1},
                   "mark-start": {"type": "number", "value": 0}, "mark-nested": {"type": "number", "value": 0},
                   "mark-back": {"type": "number", "value": 0}, "mark-middle": {"type": "number", "value": 1},
                   "mark-front": {"type": "number", "value": 2}, "mark-square": {"type": "number", "value": 0},
                   "mark-rounded": {"type": "number", "value": "0.25"}, "summary-height": {"type": "number", "value": Decimal(1) / Decimal(3)}},
        "roles": {**roles,
                  "group-band": {**roles["group-band"], "opacity": "group-opacity", "backgroundTreatment": "fill", "backgroundPaintOrder": 10},
                  "row-band": {**roles["group-band"], "opacity": "group-opacity", "backgroundTreatment": "fill", "backgroundPaintOrder": 10},
                  "group-header-band": {**roles["group-header-band"], "opacity": "group-header-opacity", "backgroundTreatment": "fill", "backgroundPaintOrder": 11},
                  "calendar-closed": {**roles["calendar-closed"], "opacity": "calendar-opacity", "backgroundTreatment": "outline", "backgroundPaintOrder": 12},
                  "milestoneSymbol": {"symbol": "milestone-symbol"}}, "metrics": {}}}


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


def test_scene_input_requires_surface_specific_network_slot_set():
    network = SimpleNamespace(surface="dependency-network")
    value = build_scene_input(projection=network, surface_content=surface_content(),
                              layout_manifest=_manifest("title", "network"),
                              resolved_theme=_theme(), font_metrics=object(), measured_sources=_measurements(),
                              capabilities={"svg": True})
    assert value.projection.surface == "dependency-network"
    with pytest.raises(SceneBuildError, match="E_PRESENTATION_SURFACE_SLOT_SET"):
        build_scene_input(projection=network, surface_content=surface_content(),
                          layout_manifest=_manifest("title", "network", "table"),
                          resolved_theme=_theme(), font_metrics=object(), measured_sources=_measurements(),
                          capabilities={"svg": True})


def test_scene_dispatches_completed_network_layout_through_registry_semantics_only():
    node = SimpleNamespace(object_id="a", title="A", order_key=("a",), critical=True, source_kind="primary")
    projection = SimpleNamespace(surface="dependency-network", network=SimpleNamespace(nodes=(node,), edges=()))
    title_bounds = Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(40))
    network_bounds = Rect(Decimal(0), Decimal(50), Decimal(400), Decimal(200))
    manifest = LayoutManifest("network", "sha256:test", "horizontal", "horizontal", Rect(Decimal(0), Decimal(0), Decimal(400), Decimal(250)), (
        LayoutDecision("title", "slot", title_bounds, "title", priority="required"),
        LayoutDecision("network", "slot", network_bounds, "network", priority="required"),
    ), row_distribution="fill", background_extents=BACKGROUND_EXTENTS)
    run = lambda source, content, role, width, block, base: MeasuredTextRun(source, content, role, Decimal(width), Decimal(block), Decimal(base), "Test Sans", 400, float(block), 1.0, "sha256:test")
    measured = MeasuredSources({}, {}, {
        "network.node.minInlineSize": Decimal(60), "network.node.minBlockSize": Decimal(30), "network.rank.gap": Decimal(12),
    }, {"title": (run(None, "Network", "heading", 80, 24, 20),), "network": (run("a", "A", "text", 20, 14, 11),)})
    value = build_scene_input(projection=projection, surface_content=surface_content(), layout_manifest=manifest,
                              resolved_theme=_theme(), font_metrics=object(), measured_sources=measured, capabilities={"svg": True})
    surface = compose_review_surface(value)
    assert surface.surface_id == "dependency-network"
    assert surface.scale_manifest is None
    assert {(node.scene_id, node.visual_role) for node in surface.primitives} >= {
        ("title", "text"), ("network-label:a", "text"), ("network-node:a", "network-node"),
    }


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
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"), "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    manifest = _manifest("title", "table", "timeline", "timeline-axis")
    value = build_scene_input(projection=projection, surface_content=surface_content((("name", "Name"),), (("a", "name", "A"),)),
                              layout_manifest=manifest, resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    assert surface.scale_manifest.domain_start == date(2026, 1, 1)
    assert any(item.scene_id == "cell:a:name" and item.text == "A" for item in surface.primitives)
    assert any(item.scene_id == "planned:a" for item in surface.primitives)
    assert any(item.scene_id == "missing-actual:a" for item in surface.primitives)
    assert next(item for item in surface.primitives if item.scene_id == "title").text_layout.font_size == 24
    assert surface.canvas_paint is not None
    assert all(item.paint is not None for item in surface.primitives)


def test_scene_completes_pattern_form_before_adapter_invocation():
    primitive = ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (0, 0, 1, 1))
    themed = _theme()
    themed["body"]["values"]["hatch"] = {"type": "pattern", "value": {"kind": "diagonal-hatch", "tileInlineSize": 6, "tileBlockSize": 6, "angle": 45, "strokeWidth": 1}}
    themed["body"]["roles"]["planned"]["pattern"] = "hatch"
    value = build_scene_input(projection=ReviewProjection((), (date(2026, 1, 1), date(2026, 1, 2)), (), ()),
                              surface_content=surface_content(), layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=themed, font_metrics=_Font(), measured_sources=_measurements(), capabilities={"svg": True})
    from chrona.presentation.scene.v05_builder import _complete_surface_paint
    completed = _complete_surface_paint(SceneSurface("s", (), (), (), None, (primitive,)), value.theme_tokens)
    assert completed.primitives[0].pattern is not None


def test_scene_projects_title_links_only_to_selected_current_title_cells():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 2, 1)},
                      None, None, ("planned",), link={"href": "https://example.test/a", "title": "Open A"})
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(
        projection=projection,
        surface_content=surface_content((("title", "Title"),), (("a", "title", "A"),),
                                        link_mode="title", title_link_columns=("title",),
                                        table_cell_objects=(("a", "title", "a", True),)),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=_theme(),
        font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    cell = next(node for node in surface.primitives if node.scene_id == "cell:a:title")
    mark = next(node for node in surface.primitives if node.scene_id == "planned:a")
    assert (cell.href, cell.link_title) == ("https://example.test/a", "Open A")
    assert mark.href is None


def test_scene_projects_row_links_to_current_marks_but_not_actual_comparison_marks():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 2, 1)},
                      {"start": date(2026, 1, 2), "finish": date(2026, 2, 2)}, None, ("planned",),
                      link={"href": "https://example.test/a"})
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 2, 2)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(
        projection=projection, surface_content=surface_content(link_mode="row"),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=_theme(),
        font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    assert next(node for node in surface.primitives if node.scene_id == "planned:a").href == "https://example.test/a"
    assert next(node for node in surface.primitives if node.scene_id == "actual:a").href is None


def test_scene_uses_declared_marker_and_projects_an_object_annotation_leader():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 11)}, None, None, ("planned",)),
                                  ReviewItem("b", "B", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 6)}, None, None, ("planned",))),
                                  (date(2026, 1, 1), date(2026, 1, 11)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"), "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    viewport = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(300))
    manifest = LayoutManifest("review", "sha256:test", "horizontal", "horizontal", viewport, (
        LayoutDecision("title", "slot", Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(40)), "title"),
        LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(40), Decimal(100), Decimal(100)), "table"),
        LayoutDecision("timeline", "slot", Rect(Decimal(100), Decimal(40), Decimal(400), Decimal(100)), "timeline"),
        LayoutDecision("axis", "slot", Rect(Decimal(100), Decimal(140), Decimal(400), Decimal(40)), "timeline-axis"),
        LayoutDecision("annotations", "slot", Rect(Decimal(500), Decimal(40), Decimal(300), Decimal(100)), "annotations", priority="required", overflow="visible-overflow"),
    ), background_extents=BACKGROUND_EXTENTS)
    theme = _theme()
    theme["body"]["values"].update({"marker": {"type": "marker", "value": {"shape": "triangle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}}})
    theme["body"]["roles"]["dependency"] = {**theme["body"]["roles"]["dependency"], "marker": "marker"}
    value = build_scene_input(projection=projection, surface_content=surface_content(
        relations=({"id": "r", "from": {"object": "a"}, "to": {"object": "b"}},),
        annotations=({"id": "note", "purpose": "callout", "anchor": {"kind": "object", "id": "a", "facet": "planned", "endpoint": "finish"},
                      "placement": {"side": "end", "alignment": "center"}, "text": "Check"},)),
        layout_manifest=manifest, resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    dependency = next(item for item in surface.primitives if item.scene_id == "relation:r")
    leader = next(item for item in surface.primitives if item.scene_id == "annotation-leader:note")
    assert dependency.marker_start is not None and dependency.marker_end is not None
    assert dependency.purpose == "dependency"
    assert dependency.points[0][0] == 500
    assert dependency.points[-1][0] == 100
    assert next(item for item in surface.primitives if item.scene_id == "planned:a").purpose == "planned"
    assert leader.points


def test_explicit_row_members_keep_fixed_mark_size_labels_and_snapshot_role():
    primary = ReviewItem("a", "Current plan", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, (), item_id="primary", source_kind="primary")
    snapshot = ReviewItem("a", "Baseline", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 8)}, None, None, (), item_id="snapshot", source_kind="snapshot")
    row = ReviewRowProjection("release", "Release", "", "primary", (primary, snapshot))
    projection = ReviewProjection((primary,), (date(2026, 1, 1), date(2026, 1, 10)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
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


def test_layout_indents_only_the_named_nonleading_hierarchy_column_and_aligns_cells() -> None:
    item = ReviewItem("a", "Indented title", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
                      None, None, (), item_id="a", source_kind="primary")
    row = ReviewRowProjection("child", "Child", "", "a", (item,), depth=2)
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 10)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8),
        "timeline.mark.blockSize": Decimal(8), "table.indent.inlineSize": Decimal(12),
    })
    columns = (
        TableColumnContent("index", "#", "end", TableColumnWidth("content", "fr", 1)),
        TableColumnContent("title", "Title", "start", TableColumnWidth("content", "content")),
    )
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(columns, (("child", "index", "7"), ("child", "title", "Indented title")),
                                                              table_hierarchy_column="title"),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)
    index = next(node for node in surface.primitives if node.scene_id == "cell:child:index")
    title = next(node for node in surface.primitives if node.scene_id == "cell:child:title")
    title_column = next(node for node in surface.primitives if node.scene_id == "column:title")
    assert index.bounds[0] > 0
    assert title.bounds[0] == title_column.bounds[0] + 24


def test_scene_projects_layout_completed_rollup_summary_bar():
    rollup = ReviewItem("programme", "Programme", "span",
                        {"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
                        None, None, (), item_id="programme", source_kind="primary")
    row = ReviewRowProjection("programme", "Programme", "", "programme", (rollup,),
                              rollup_presentation="bar")
    projection = ReviewProjection((rollup,), (date(2026, 1, 1), date(2026, 1, 10)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(9)})
    value = build_scene_input(projection=projection, surface_content=surface_content(),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})

    surface = compose_review_surface(value)
    summary_bar = next(item for item in surface.primitives if item.scene_id == "summary-bar:programme")

    assert summary_bar.kind == "Rect"
    assert summary_bar.purpose == "summary-bar"
    assert summary_bar.visual_role == "summary-bar"
    assert summary_bar.bounds[2] > 0
    assert summary_bar.bounds[3] == 3


def test_scene_projects_selected_inside_label_with_its_host_mark_role():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 11)},
                      None, None, ("planned",), source_kind="primary")
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 11)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(20)})
    value = build_scene_input(
        projection=projection,
        surface_content=surface_content(show_member_labels=True, label_placement="plot", label_content=("title",),
                                        label_side="inside", label_overflow="visible-overflow"),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=_theme(),
        font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True},
    )
    surface = compose_review_surface(value)
    label = next(node for node in surface.primitives if node.scene_id == "member-label:a")
    assert label.visual_role == "member-label-inside-planned"


def test_scene_anchors_an_explicit_actual_inside_label_to_its_actual_mark():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 11)},
                      {"start": date(2026, 1, 2), "finish": date(2026, 1, 12)}, None, ("planned", "actual"),
                      item_id="actual", source_kind="actual")
    row = ReviewRowProjection("release", "Release", "", "actual", (item,))
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 12)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(48), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(20)})
    value = build_scene_input(
        projection=projection,
        surface_content=surface_content(show_member_labels=True, label_placement="plot", label_content=("title",),
                                        label_side="inside", label_overflow="visible-overflow"),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=_theme(),
        font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True},
    )
    surface = compose_review_surface(value)
    label = next(node for node in surface.primitives if node.scene_id == "member-label:release:actual")
    actual = next(node for node in surface.primitives if node.scene_id == "actual:release:actual")
    assert label.visual_role == "member-label-inside-actual"
    assert actual.bounds[0] <= label.bounds[0] and label.bounds[2] <= actual.bounds[0] + actual.bounds[2]


def test_scene_falls_back_from_short_inside_label_to_outside_text_role():
    item = ReviewItem("a", "Long label", "span", {"start": date(2026, 1, 10), "end": date(2026, 1, 11)},
                      None, None, ("planned",), source_kind="primary")
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(20)})
    value = build_scene_input(
        projection=projection,
        surface_content=surface_content(show_member_labels=True, label_placement="plot", label_content=("title",),
                                        label_side="inside", label_fallback=("inside", "above"), label_overflow="visible-overflow"),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=_theme(),
        font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True},
    )
    surface = compose_review_surface(value)
    label = next(node for node in surface.primitives if node.scene_id == "member-label:a")
    assert label.visual_role == "text"


def test_scene_projects_only_accepted_typed_plot_labels_and_relations():
    projection = ReviewProjection((
        ReviewItem("a", "A very long label", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, ()),
        ReviewItem("b", "B", "span", {"start": date(2026, 1, 2), "end": date(2026, 1, 9)}, None, None, ()),
    ), (date(2026, 1, 1), date(2026, 1, 10)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    rect = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(1000))
    manifest = LayoutManifest("review", "sha256:test", "horizontal", "horizontal", rect,
                              tuple(LayoutDecision(source, "slot", rect, source)
                                    for source in ("title", "table", "timeline", "timeline-axis")),
                              relation_max_bends=0, row_distribution="fill", background_extents=BACKGROUND_EXTENTS)
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
    label = next(item for item in surface.primitives if item.scene_id == "member-label:a")
    planned = next(item for item in surface.primitives if item.scene_id == "planned:a")
    assert label.bounds[1] + label.bounds[3] <= planned.bounds[1]
    assert not any(item.scene_id.startswith("relation:depends") for item in surface.primitives)


def test_same_explicit_row_relation_uses_distinct_mark_ports():
    first = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 4)}, None, None, (), item_id="a", source_kind="primary")
    second = ReviewItem("b", "B", "span", {"start": date(2026, 1, 5), "end": date(2026, 1, 9)}, None, None, (), item_id="b", source_kind="primary")
    row = ReviewRowProjection("phase", "Phase", "", "a", (first, second))
    projection = ReviewProjection((first, second), (date(2026, 1, 1), date(2026, 1, 9)), (), (), (row,))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    theme = _theme()
    theme["body"]["values"]["marker"] = {"type": "marker", "value": {"shape": "triangle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}}
    theme["body"]["roles"]["dependency"] = {**theme["body"]["roles"]["dependency"], "marker": "marker"}
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
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
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
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
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
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8),
                                   "timeline.groupHeader.blockSize": Decimal(20)})
    value = build_scene_input(projection=projection, surface_content=surface_content(group_presentation="header"),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    assert any(node.scene_id == "group-header:fw" and node.text == "Firmware team"
               for node in surface.primitives)
    assert surface.groups[0].header_bounds is not None


def test_header_fold_projects_mark_label_route_and_annotation_without_a_point_table_row():
    span = ReviewItem("task", "Task", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 4)},
                      None, None, (), group_id="fw", group_label="Firmware team", item_id="task")
    point = ReviewItem("gate", "Release gate", "point", {"at": date(2026, 1, 5)},
                       {"at": date(2026, 1, 6)}, None, (), group_id="fw", group_label="Firmware team",
                       item_id="gate", source_kind="combined", track="shared")
    scenario = ReviewItem("gate", "Baseline gate", "point", {"at": date(2026, 1, 4)},
                          None, None, (), group_id="fw", group_label="Firmware team",
                          item_id="scenario:baseline:gate", source_kind="scenario", track="shared")
    row = ReviewRowProjection("fw-row", "Task", "fw", "task", (span,))
    projection = ReviewProjection((span, point), (date(2026, 1, 1), date(2026, 1, 6)), (), (), (row,),
                                  folded_points=(FoldedPointProjection(point, "fw", members=(scenario,)),))
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8),
        "timeline.groupHeader.blockSize": Decimal(20),
    })
    viewport = Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(400))
    manifest = LayoutManifest("review", "sha256:test", "horizontal", "horizontal", viewport, (
        LayoutDecision("title", "slot", Rect(Decimal(0), Decimal(0), Decimal(1000), Decimal(40)), "title"),
        LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(40), Decimal(100), Decimal(160)), "table"),
            LayoutDecision("timeline", "slot", Rect(Decimal(100), Decimal(60), Decimal(700), Decimal(140)), "timeline"),
        LayoutDecision("axis", "slot", Rect(Decimal(100), Decimal(200), Decimal(700), Decimal(40)), "timeline-axis"),
        LayoutDecision("annotations", "slot", Rect(Decimal(800), Decimal(40), Decimal(200), Decimal(160)), "annotations"),
    ), row_distribution="fill", background_extents=BACKGROUND_EXTENTS)
    theme = _theme()
    theme["body"]["values"]["marker"] = {"type": "marker", "value": {"shape": "triangle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}}
    theme["body"]["roles"]["dependency"] = {**theme["body"]["roles"]["dependency"], "marker": "marker"}
    value = build_scene_input(projection=projection, surface_content=surface_content(
        table_columns=(("name", "Name"),), table_cells=(("task", "name", "Task"),),
        group_presentation="header", label_placement="plot", label_content=("title",), label_overflow="visible-overflow",
        relations=({"id": "task-gate", "from": {"object": "task"}, "to": {"object": "gate"}},),
        annotations=({"id": "gate-note", "purpose": "callout", "anchor": {"kind": "object", "id": "gate", "facet": "planned", "endpoint": "at"},
                      "placement": {"side": "end", "alignment": "center"}, "text": "Review"},),
    ), layout_manifest=manifest, resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement,
        capabilities={"svg": True})

    surface = compose_review_surface(value)

    assert not any(node.scene_id.startswith("cell:gate:") for node in surface.primitives)
    assert any(node.scene_id == "planned:group-header:fw:gate" for node in surface.primitives)
    assert any(node.scene_id == "actual:group-header:fw:gate" for node in surface.primitives)
    assert any(node.scene_id == "planned:group-header:fw:scenario:baseline:gate" for node in surface.primitives)
    assert any(node.scene_id == "member-label:group-header:fw:gate" and node.text == "Release gate"
               for node in surface.primitives)
    assert any(node.scene_id.startswith("relation:task-gate:") for node in surface.primitives)
    assert any(node.scene_id == "annotation-leader:gate-note" for node in surface.primitives)


def test_declared_actual_cutoff_emits_as_of_marker_only_within_window():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 10)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
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
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content(calendar_closed=(date(2026, 1, 3),)),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    closure = next(node for node in surface.primitives if node.scene_id == "calendar-closed:2026-01-03")
    assert closure.visual_role == "calendar-closed"
    assert closure.paint.fill is None and closure.paint.stroke == "#102030"
    assert closure.bounds[2] < 1000


def test_layout_projects_alternate_row_bands_only_into_the_declared_table_region():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 3)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 3)), (), ())
    manifest = LayoutManifest("review", "sha256:test", "horizontal", "horizontal", Rect(Decimal(0), Decimal(0), Decimal(500), Decimal(200)), (
        LayoutDecision("title", "slot", Rect(Decimal(0), Decimal(0), Decimal(500), Decimal(20)), "title"),
        LayoutDecision("table", "slot", Rect(Decimal(0), Decimal(20), Decimal(100), Decimal(100)), "table"),
        LayoutDecision("timeline", "slot", Rect(Decimal(120), Decimal(20), Decimal(300), Decimal(100)), "timeline"),
        LayoutDecision("axis", "slot", Rect(Decimal(120), Decimal(120), Decimal(300), Decimal(20)), "timeline-axis"),
    ), background_extents=BACKGROUND_EXTENTS)
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8),
    })
    theme = _theme()
    theme["body"]["roles"]["row-band"] = {**theme["body"]["roles"]["row-band"], "backgroundTreatment": "outline"}
    surface = compose_review_surface(build_scene_input(
        projection=projection, surface_content=surface_content(row_decoration="alternate-rows"), layout_manifest=manifest,
        resolved_theme=theme, font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True},
    ))
    band = next(node for node in surface.primitives if node.scene_id.startswith("row-band:"))
    assert band.bounds == (0.0, 20.0, 100.0, 40.0)
    assert band.slot_id == "table"
    assert band.paint.fill is None and band.paint.stroke == "#102030"
    assert not any(node.scene_id.startswith("group:") for node in surface.primitives)


def test_layout_rejects_intersecting_translucent_background_fills_before_scene():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 4)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 4)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8),
    })
    theme = _theme()
    theme["body"]["roles"]["calendar-closed"] = {**theme["body"]["roles"]["calendar-closed"], "backgroundTreatment": "fill"}
    with pytest.raises(SceneBuildError, match="E_LAYOUT_BACKGROUND_OVERLAP"):
        compose_review_surface(build_scene_input(
            projection=projection, surface_content=surface_content(calendar_closed=(date(2026, 1, 2),)),
            layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=theme,
            font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True},
        ))


def test_narrow_calendar_density_retains_only_declared_exception_closures():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))}, {
        "text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
        "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8),
        "timeline.calendarClosed.minimumDayWidth": Decimal(500),
    })
    value = build_scene_input(projection=projection, surface_content=surface_content(
        calendar_closed=(date(2026, 1, 2), date(2026, 1, 3)), calendar_exceptions=(date(2026, 1, 2),)),
        layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"), resolved_theme=_theme(),
        font_metrics=_Font(), measured_sources=measurement, capabilities={"svg": True})
    surface = compose_review_surface(value)
    closure_ids = {node.scene_id for node in surface.primitives if node.scene_id.startswith("calendar-closed:")}
    assert closure_ids == {"calendar-closed:2026-01-02"}


def test_declared_axis_tiers_emit_their_own_band_grid_and_label_primitives():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2027, 1, 1)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2027, 1, 1)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection, surface_content=surface_content(axis_tiers=(
                                  AxisTier("quarter", 1, "band"), AxisTier("quarter", 1, "grid-major"),
                                  AxisTier("month", 1, "grid-minor"),
                                  AxisTier("quarter", 1, "labels", AxisLabelIntent("year-quarter", (), "center", "visible-overflow")),
                              )),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)

    assert any(node.scene_id.startswith("axis-band-rect:") for node in surface.primitives)
    assert any(node.scene_id.startswith("axis-label:") for node in surface.primitives)
    grids = [node for node in surface.primitives if node.scene_id.startswith("axis-grid:")]
    assert {node.visual_role for node in grids} == {"axis-major", "axis-minor"}
    assert all(node.points[0][1] == next(slot.bounds[1] for slot in surface.slots if slot.source == "timeline")
               for node in grids)


def test_layout_records_auto_candidate_and_completed_axis_label_measurements():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 7, 1)}, None, None, ())
    projection = ReviewProjection((item,), (date(2026, 1, 1), date(2026, 7, 1)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    content = surface_content(axis_tiers=(
        AxisTier("quarter", 1, "band"),
        AxisTier("auto", 2, "labels", AxisLabelIntent(None, (("month", "short-month"), ("quarter", "year-quarter")), "center", "thin-with-record")),
    ))
    value = build_scene_input(projection=projection, surface_content=content,
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    composition = compose_surface_layout(SurfaceLayoutRequest(
        projection=value.projection, presentation_contract=normalize_presentation_input(content),
        surface_content=content, layout_manifest=value.layout_manifest, measured_sources=value.measured_sources,
        theme_tokens=value.theme_tokens, font_metrics=value.font_metrics, locale=value.locale,
        capabilities=dict(value.capabilities),
    ))

    band, labels = composition.placement.axis_tier_outcomes
    assert (band.role, band.selected_unit, band.label_form) == ("band", "quarter", None)
    assert (labels.requested_units, labels.selected_unit, labels.every, labels.label_form) == (
        ("month", "quarter"), "month", 2, "short-month")
    assert [item.candidate_id for item in labels.intervals] == ["axis-label:1:0", "axis-label:1:2", "axis-label:1:4"]
    assert all(item.label is not None and item.label_fits and item.disposition == "placed" for item in labels.intervals)


def test_table_columns_use_measured_non_overlapping_origins():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    measurement = MeasuredSources({"title": _title_measurement()}, {"title": SourceInput(("Plan",))},
                                  {"text.body.size": Decimal(14), "text.body.lineHeight": Decimal("1.4"),
                                   "timeline.row.minBlockSize": Decimal(40), "timeline.row.paddingBlock": Decimal(8), "timeline.mark.blockSize": Decimal(8)})
    value = build_scene_input(projection=projection,
                              surface_content=surface_content((("long", "Long heading"), ("short", "B")),
                                                                (("a", "long", "a deliberately long table value"), ("a", "short", "B"))),
                              layout_manifest=_manifest("title", "table", "timeline", "timeline-axis"),
                              resolved_theme=_theme(), font_metrics=_Font(), measured_sources=measurement,
                              capabilities={"svg": True})
    surface = compose_review_surface(value)
    assert next(item for item in surface.primitives if item.scene_id == "column:short").bounds[0] > next(item for item in surface.primitives if item.scene_id == "column:long").bounds[0]
    assert [column.column_id for column in surface.columns] == ["long", "short"]
    cell = next(item for item in surface.primitives if item.scene_id == "cell:a:long")
    assert (cell.table_row_id, cell.table_column_id) == ("a", "long")
