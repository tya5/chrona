"""The render use case is callable with a closure, without a command line."""
from __future__ import annotations

import tempfile
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
import jsonschema
import yaml

import chrona.usecases.render_review as render_usecase
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, obstacles_intersect
from chrona.presentation.layout.surface_composer import _lane_fallback_clears_required_labels
from chrona.presentation.layout.surface_quality import TextPlacement
from chrona.presentation.contracts.resources import ViewLaneLabel, ViewLaneTable, ViewRowMode
from chrona.presentation.contracts import parse_contract
from chrona.presentation.model.surface_content import TableCellContent, TableColumnContent, TableColumnWidth, TableContent
from chrona.presentation.model.closure import RenderClosure, resolve_render_context
from chrona.presentation.model.theme_tokens import ThemeTokenError
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.presentation.scene.paint import ScenePaintError
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.render_review import (
    RenderFailed, RenderRequest, _font_warnings, _warnings_from_findings, render_review,
)
from chrona.presentation.scene.perceptibility import ScenePerceptibilityFinding
from chrona.presentation.model.font_metrics import FontGlyphSubstitution
from chrona.presentation.scene.serialization import SceneSerializationError, _references_are_closed, _surface, scene_document, serialize_scene, validate_scene_document
from chrona.presentation.scene.model import (
    SceneLaneMember, SceneLaneObstacle, SceneLaneRectObstacle, SceneLaneSegmentObstacle,
    ScenePrimitive, SceneRow, SceneSlot, SceneSurface,
)
from chrona.resources import schema_document


def test_font_substitution_warning_only_claims_raster_draw_result():
    substitution = FontGlyphSubstitution("Requested", "Metrics only", 400, 0x2705, "✅")
    assert _font_warnings((substitution,), "png")[0].drawn is False
    assert _font_warnings((substitution,), "pdf")[0].drawn is False
    assert _font_warnings((substitution,), "svg")[0].drawn is None


def test_lane_source_measurement_uses_exact_membership_table_and_lane_count():
    items = (SimpleNamespace(title="Long candidate title", group_label="Avionics"),
             SimpleNamespace(title="Short", group_label="Avionics"))
    projection = SimpleNamespace(
        lane_rows=(SimpleNamespace(lane_id="lane:g:a", group_id="g", items=items),),
        items=items, window=(date(2026, 1, 1), date(2026, 1, 31)), network=None,
    )
    view = SimpleNamespace(
        rows=SimpleNamespace(mode=ViewRowMode.LANES,
                             lane_table=ViewLaneTable(ViewLaneLabel.GROUP, True)),
        table_columns=(),
    )
    table = TableContent((TableColumnContent("Lane", "Lane", "start", TableColumnWidth("content", "content")),
                          TableColumnContent("Items", "Items", "end", TableColumnWidth("content", "content"))),
                         (TableCellContent("lane:g:a", "Lane", "Avionics", "tableCell"),
                          TableCellContent("lane:g:a", "Items", "2", "tableCell", "numeric")), (), None, ())
    sources = render_usecase._source_inputs(
        {"project": {"title": "test"}}, view, projection, SimpleNamespace(runs=()), table=table,
    )

    assert sources["table"].item_count == sources["timeline"].item_count == 1
    assert tuple(column.column_id for column in sources["table"].table.columns) == ("Lane", "Items")
    assert [cell.content for cell in sources["table"].table.cells] == ["Avionics", "2"]


def test_lane_measurement_identity_uses_effective_theme_and_font_asset():
    frame = SimpleNamespace(inline_scale=SimpleNamespace(scale_id="primary"))
    font = SimpleNamespace(content_identity="sha256:font")
    first = render_usecase._lane_measurement_identity({"body": {"value": 1}}, font, frame)
    second = render_usecase._lane_measurement_identity({"body": {"value": 2}}, font, frame)
    assert first.theme_identity != second.theme_identity
    assert first.font_asset_identity == "sha256:font"
    assert first.scale_identity == "primary"


def test_scene_error_findings_become_draft_warnings_without_information_duplication():
    error = ScenePerceptibilityFinding("v1", "E_SCENE_TEXT_OCCLUDED", "error", "/surfaces/0:review",
                                       ("text", "cover"), "timeline", (("coverageRatio", 1.0),))
    info = ScenePerceptibilityFinding("v1", "I_SCENE_PAINT_CONTRAST", "info", "/surfaces/0:review",
                                      ("tint",), "timeline", (("contrastRatio", 1.1),))

    warnings = _warnings_from_findings((error, info))

    assert [(item.code, item.finding_code, item.primitive_ids) for item in warnings] == [
        ("W_SCENE_TEXT_OCCLUDED", "E_SCENE_TEXT_OCCLUDED", ("text", "cover")),
    ]


from tools.materialize_example import _copy_context_closure

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = ROOT / "examples/halcyon-1"


def test_lane_visible_route_fallback_never_crosses_required_member_text():
    label = TextPlacement("member-label:a", "a", "A",
                          Rect(Decimal(10), Decimal(10), Decimal(20), Decimal(10)),
                          "text", semantic_id="memberLabel")
    crossing = ((0.0, 15.0), (40.0, 15.0))
    clear = ((0.0, 25.0), (40.0, 25.0))
    assert not _lane_fallback_clears_required_labels(crossing, (label,))
    assert _lane_fallback_clears_required_labels(clear, (label,))
    assert _lane_fallback_clears_required_labels(crossing, (replace(label, overflow="suppressed"),))


def _closure(temporary: Path, context_name: str = "02-programme-board"):
    snapshot = temporary / "snapshot"
    snapshot.mkdir()
    reference, _ = _copy_context_closure(EXAMPLE.resolve(), EXAMPLE / f"contexts/{context_name}.yaml", snapshot)
    reader = LocalSnapshotReader(snapshot, reference["store"]["identity"])
    return resolve_render_context(reference, reader), snapshot


def _request(closure, snapshot, **kwargs):
    return RenderRequest(closure, snapshot, ReferenceScheduler(), V05SvgRenderer(), **kwargs)


def test_render_review_renders_a_closure_without_the_cli():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        rendered = render_review(_request(closure, snapshot))
    assert rendered.artifact.content == (EXAMPLE / "generated/02-programme-board.svg").read_bytes()
    assert rendered.surface.primitives
    assert rendered.scene.surfaces == (rendered.surface,)
    assert rendered.scene.provenance.mode == "immutable"
    assert rendered.scene.manifest.visual_role_counts
    assert {"project", "view", "layout-profile"} <= rendered.read_inputs


@pytest.mark.parametrize("context_name", ["02-programme-board", "11-overlay-briefing", "12-glyph-gates"])
def test_hidden_lane_layout_projects_fixed_membership_before_public_activation(context_name):
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary), context_name)
        value = yaml.safe_load((EXAMPLE / "views/02-programme-board.yaml").read_text(encoding="utf-8"))
        value["version"] = "chrona/view/v0.28"
        body = value["body"]
        body.pop("tableColumns", None)
        body["rows"] = {"mode": "lanes", "packing": ["explicit", "attached", "chain", "dates"],
                        "laneTable": {"label": "group", "count": True}}
        body["visibility"]["labels"] = {"placement": "plot"}
        contract = parse_contract(closure.view.identity, value)
        resources = tuple(replace(resource, contract=contract) if resource.kind == "view" else resource
                          for resource in closure.resources)
        lane_closure = replace(closure, resources=resources)
        with pytest.raises(RenderFailed, match="E_REVIEW_LANE_ENGINE_UNAVAILABLE"):
            render_review(_request(lane_closure, snapshot))
        rendered = render_usecase._render_review(_request(lane_closure, snapshot))

    assert rendered.surface.primitives
    assert rendered.scene.surfaces == (rendered.surface,)
    assert 0 < len(rendered.surface.rows) < 26
    assert all(row.row_id.startswith("review-lane:") for row in rendered.surface.rows)
    timeline_slot = next(slot for slot in rendered.surface.slots if slot.source == "timeline")
    assert max(row.bounds[1] + row.bounds[3] for row in rendered.surface.rows) <= (
        timeline_slot.bounds[1] + timeline_slot.bounds[3]
    )
    assert any(item.scene_id.startswith("member-label:") for item in rendered.surface.primitives)
    suppressed = sum(item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
                     for item in rendered.surface.diagnostics)
    counted = sum(item.count for item in rendered.surface.info_diagnostics
                  if item.code == "I_LAYOUT_PLOT_LABELS_SUPPRESSED")
    assert counted == suppressed
    causes = [json.loads(item.removeprefix("I_LAYOUT_LANE_ROUTE_CAUSE:"))
              for item in rendered.surface.diagnostics
              if item.startswith("I_LAYOUT_LANE_ROUTE_CAUSE:")]
    assert all(cause["primaryCause"] != "egress-collision" for cause in causes)
    assert len(causes) == sum(item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")
                              for item in rendered.surface.diagnostics)
    labels = [ObstacleRect(item.bounds[0], item.bounds[1],
                           item.bounds[0] + item.bounds[2], item.bounds[1] + item.bounds[3])
              for item in rendered.surface.primitives
              if item.kind == "Text" and item.purpose in {"member-label", "finish-delta"}]
    for relation in (item for item in rendered.surface.primitives if item.purpose == "dependency"):
        for start, end in zip(relation.points, relation.points[1:]):
            assert all(not obstacles_intersect(ObstacleSegment(start, end), label)
                       for label in labels), relation.scene_id


def test_hidden_lane_layout_budgets_overlapping_authored_members_before_final_allocation(monkeypatch):
    completed = []
    original = render_usecase.preflight_fixed_lane_layout

    def capture(**kwargs):
        result = original(**kwargs)
        completed.append(result)
        return result

    monkeypatch.setattr(render_usecase, "preflight_fixed_lane_layout", capture)
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        value = yaml.safe_load((EXAMPLE / "views/02-programme-board.yaml").read_text(encoding="utf-8"))
        value["version"] = "chrona/view/v0.28"
        body = value["body"]
        body.pop("tableColumns", None)
        body["rows"] = {"mode": "lanes", "laneTable": {"label": "group", "count": True},
                        "laneKeys": {"byObject": {"structure": "dense", "eps": "dense"}}}
        body["visibility"]["labels"] = {"placement": "plot", "content": ["title"], "side": "inside"}
        body["visibility"]["fallback"] = {"labels": ["inside", "end", "suppress"]}
        contract = parse_contract(closure.view.identity, value)
        resources = tuple(replace(resource, contract=contract) if resource.kind == "view" else resource
                          for resource in closure.resources)
        rendered = render_usecase._render_review(_request(replace(closure, resources=resources), snapshot))

    lane = next(item for item in rendered.surface.rows if '"dense"' in item.row_id)
    timeline = next(item for item in rendered.surface.slots if item.source == "timeline")
    assert len(completed) == 1
    assert next(item for item in completed[0].subtracks.lanes if item.lane_id == lane.row_id).subtrack_count > 1
    assert timeline.bounds[3] >= float(completed[0].natural_block_requirement)
    assert max(row.bounds[1] + row.bounds[3] for row in rendered.surface.rows) <= (
        timeline.bounds[1] + timeline.bounds[3]
    )
    assert not any(item.startswith(("W_LAYOUT_ROW_DENSITY", "W_LAYOUT_MARK_OVERFLOW"))
                   for item in rendered.surface.diagnostics)


@pytest.mark.parametrize("error", [
    LayoutError("E_LAYOUT_METRIC_REQUIRED", "/body/metrics/example", detail="missing metric"),
    ThemeTokenError("E_THEME_ROLE_REQUIRED", "/body/roles/example/fontFamily"),
    ScenePaintError("E_PRESENTATION_PAINT_INVALID", "/body/roles/example/strokeWidth", "invalid width"),
])
def test_render_review_transports_typed_presentation_failure_pointer(monkeypatch, error):
    def fail(_request):
        raise error

    monkeypatch.setattr(render_usecase, "_render_review", fail)
    with pytest.raises(RenderFailed) as failed:
        render_review(None)
    assert failed.value.code == error.diagnostic_id
    assert failed.value.source_ref == error.path
    assert failed.value.component == "presentation"


def test_completed_scene_serializes_deterministically_with_typed_table_links():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        scene = render_review(_request(closure, snapshot)).scene
    first, second = serialize_scene(scene), serialize_scene(scene)
    assert first == second
    document = json.loads(first)
    cells = [item for item in document["surfaces"][0]["primitives"] if item["purpose"] == "table-cell"]
    assert cells and all("tableRowId" in item and "tableColumnId" in item for item in cells)
    assert document["manifest"]["visualRoleCounts"]
    slots = {item["id"] for item in document["surfaces"][0]["slots"]}
    assert slots and all(item["slotId"] in slots for item in document["surfaces"][0]["primitives"])


def test_scene_validation_rejects_a_table_reference_not_owned_by_its_surface():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        document = scene_document(render_review(_request(closure, snapshot)).scene)
    cell = next(item for item in document["surfaces"][0]["primitives"] if item["purpose"] == "table-cell")
    cell["tableColumnId"] = "not-a-column"
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_scene_validation_rejects_a_primitive_slot_not_owned_by_its_surface():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        document = scene_document(render_review(_request(closure, snapshot)).scene)
    document["surfaces"][0]["primitives"][0]["slotId"] = "missing-slot"
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_scene_validation_requires_layout_completed_canvas_bounds():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        document = scene_document(render_review(_request(closure, snapshot)).scene)
    document["surfaces"][0].pop("canvasBounds")
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_scene_lane_anchor_and_primitive_identity_are_optional_and_serialized_typed():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        scene = render_review(_request(closure, snapshot)).scene
    original = serialize_scene(scene)
    surface = scene.surfaces[0]
    row = surface.rows[0]
    anchored = replace(row, lane_mark_band_block=row.bounds[1] + row.bounds[3] / 2)
    rows = (anchored, *surface.rows[1:])
    primitive = surface.primitives[0]
    marked = replace(primitive, lane_row_id=anchored.row_id, lane_member_id="member-1")
    projected = replace(scene, surfaces=(replace(surface, rows=rows,
                                                  primitives=(marked, *surface.primitives[1:])),))

    document = json.loads(serialize_scene(projected))
    projected_surface = document["surfaces"][0]
    assert projected_surface["rows"][0]["laneMarkBandBlock"] == anchored.lane_mark_band_block
    assert projected_surface["primitives"][0]["laneRowId"] == anchored.row_id
    assert projected_surface["primitives"][0]["laneMemberId"] == "member-1"
    assert "laneMarkBandBlock" not in scene_document(scene)["surfaces"][0]["rows"][0]
    assert "laneRowId" not in scene_document(scene)["surfaces"][0]["primitives"][0]
    assert original == serialize_scene(scene)


def test_scene_lane_carrier_rejects_partial_or_unanchored_references():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (0, 0, 1, 1),
                       lane_row_id="row")
    primitive = ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (0, 0, 1, 1),
                               lane_row_id="missing", lane_member_id="member")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneSurface("s", (), (SceneRow("a", "g", (0, 0, 10, 10), "row"),), (), None, (primitive,))
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneRow("a", "g", (0, 0, 10, 10), "row", float("nan"))


def test_scene_document_lane_reference_requires_an_in_bounds_anchor():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        document = scene_document(render_review(_request(closure, snapshot)).scene)
    surface = document["surfaces"][0]
    row = surface["rows"][0]
    row["laneMarkBandBlock"] = row["bounds"]["block"] + row["bounds"]["blockSize"] / 2
    primitive = surface["primitives"][0]
    primitive["laneRowId"] = row["id"]
    primitive["laneMemberId"] = "member-1"
    validate_scene_document(document)
    row["laneMarkBandBlock"] = row["bounds"]["block"] + row["bounds"]["blockSize"] + 1
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_lane_surface_carries_closed_member_emission_inventory():
    row = SceneRow("object", "group", (0, 0, 20, 12), "lane-1", 2)
    mark = ScenePrimitive("mark-1", "Rect", "object", "object", "planned", "planned",
                          (1, 2, 4, 2), slot_id="slot", lane_row_id="lane-1", lane_member_id="member-1")
    label = ScenePrimitive("label-1", "Text", "object", "review", "member-label", "taskTitle",
                           (2, 5, 6, 2), slot_id="slot", lane_row_id="lane-1", lane_member_id="member-1")
    member = SceneLaneMember("lane-1", "member-1", ("mark-1", "label-1"), ("mark-1",))
    obstacles = (
        SceneLaneObstacle("facet-mark", "mark-1", "lane-1", "member-1", "mark",
                          SceneLaneRectObstacle(1, 2, 5, 4)),
        SceneLaneObstacle("facet-label", "label-1", "lane-1", "member-1", "required-label",
                          SceneLaneSegmentObstacle((2, 5), (8, 5), 1)),
    )
    surface = SceneSurface("s", (SceneSlot("slot", "timeline", None, (0, 0, 20, 12)),),
                           (row,), (), None, (mark, label), lane_mode="lanes",
                           canvas_bounds=(0, 0, 20, 12),
                           lane_members=(member,), lane_obstacles=obstacles, lane_clearance=0.5)

    document = _surface(surface)
    schema = schema_document("scene-v0.6.schema.yaml")
    jsonschema.Draft202012Validator({"$ref": "#/$defs/surface", "$defs": schema["$defs"]}).validate(document)
    assert _references_are_closed({"surfaces": [document]})
    assert document["laneMode"] == "lanes"
    assert document["laneMembers"] == [{
        "rowId": "lane-1", "memberId": "member-1",
        "emittedPrimitiveIds": ["mark-1", "label-1"], "primaryMarkIds": ["mark-1"],
    }]
    assert document["laneObstacles"] == [
        {"facetId": "facet-mark", "primitiveId": "mark-1", "rowId": "lane-1",
         "memberId": "member-1", "class": "mark",
         "geometry": {"kind": "rect", "left": 1, "top": 2, "right": 5, "bottom": 4}},
        {"facetId": "facet-label", "primitiveId": "label-1", "rowId": "lane-1",
         "memberId": "member-1", "class": "required-label",
         "geometry": {"kind": "stroked-segment", "start": [2, 5], "end": [8, 5],
                      "strokeWidth": 1}},
    ]
    assert document["laneClearance"] == 0.5
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        replace(surface, lane_clearance=-0.1)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator({"$ref": "#/$defs/surface", "$defs": schema["$defs"]}).validate(
            {key: value for key, value in document.items() if key != "laneMode"})
    without_inventory = {key: value for key, value in document.items() if key != "laneMembers"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator({"$ref": "#/$defs/surface", "$defs": schema["$defs"]}).validate(
            without_inventory)


def test_lane_document_reference_check_rejects_malformed_geometry_without_type_error():
    row = SceneRow("object", "group", (0, 0, 20, 12), "lane-1", 2)
    mark = ScenePrimitive("mark-1", "Rect", "object", "object", "planned", "planned",
                          (1, 2, 4, 2), slot_id="slot", lane_row_id="lane-1", lane_member_id="member-1")
    member = SceneLaneMember("lane-1", "member-1", ("mark-1",), ("mark-1",))
    obstacle = SceneLaneObstacle("facet-mark", "mark-1", "lane-1", "member-1", "mark",
                                  SceneLaneRectObstacle(1, 2, 5, 4))
    surface = SceneSurface("s", (SceneSlot("slot", "timeline", None, (0, 0, 20, 12)),),
                           (row,), (), None, (mark,), lane_mode="lanes",
                           canvas_bounds=(0, 0, 20, 12), lane_members=(member,),
                           lane_obstacles=(obstacle,), lane_clearance=0.5)
    document = _surface(surface)
    document["laneObstacles"][0]["geometry"]["left"] = "not-a-number"
    assert not _references_are_closed({"surfaces": [document]})

    document["laneObstacles"][0]["geometry"]["left"] = 1
    document["laneClearance"] = "not-a-number"
    assert not _references_are_closed({"surfaces": [document]})

    document["laneClearance"] = 0.5
    document["laneObstacles"][0]["geometry"] = {
        "kind": "stroked-segment", "start": [1, "not-a-number"],
        "end": [5, 4], "strokeWidth": 1,
    }
    assert not _references_are_closed({"surfaces": [document]})


@pytest.mark.parametrize("broken", ["missing", "unknown-primitive", "wrong-member", "duplicate-facet"])
def test_lane_surface_requires_exact_obstacle_identity_coverage(broken):
    row = SceneRow("object", "group", (0, 0, 20, 12), "lane-1", 2)
    mark = ScenePrimitive("mark-1", "Rect", "object", "object", "planned", "planned",
                          (1, 2, 4, 2), lane_row_id="lane-1", lane_member_id="member-1")
    label = ScenePrimitive("label-1", "Text", "object", "review", "member-label", "taskTitle",
                           (2, 5, 6, 2), lane_row_id="lane-1", lane_member_id="member-1")
    member = SceneLaneMember("lane-1", "member-1", ("mark-1", "label-1"), ("mark-1",))
    mark_obstacle = SceneLaneObstacle("facet-mark", "mark-1", "lane-1", "member-1", "mark",
                                      SceneLaneRectObstacle(1, 2, 5, 4))
    label_obstacle = SceneLaneObstacle("facet-label", "label-1", "lane-1", "member-1", "required-label",
                                       SceneLaneRectObstacle(2, 5, 8, 7))
    obstacles = (mark_obstacle, label_obstacle)
    if broken == "missing":
        obstacles = (mark_obstacle,)
    elif broken == "unknown-primitive":
        obstacles = (mark_obstacle, replace(label_obstacle, primitive_id="unlisted"))
    elif broken == "wrong-member":
        obstacles = (mark_obstacle, replace(label_obstacle, member_id="other"))
    elif broken == "duplicate-facet":
        obstacles = (mark_obstacle, replace(label_obstacle, facet_id="facet-mark"))

    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneSurface("s", (), (row,), (), None, (mark, label), lane_mode="lanes",
                     lane_members=(member,), lane_obstacles=obstacles, lane_clearance=0.5)


@pytest.mark.parametrize("broken", [
    "inventory-omits-tagged", "inventory-mismatched-tags", "untagged-member-purpose",
    "unknown-primary-mark", "untagged-missing-actual", "untagged-progress-fill",
    "untagged-summary-bar", "comparison-primary",
])
def test_lane_surface_rejects_incomplete_or_inconsistent_member_inventory(broken):
    row = SceneRow("object", "group", (0, 0, 20, 12), "lane-1", 2)
    mark = ScenePrimitive("mark-1", "Rect", "object", "object", "planned", "planned",
                          (1, 2, 4, 2), lane_row_id="lane-1", lane_member_id="member-1")
    label = ScenePrimitive("label-1", "Text", "object", "review", "member-label", "taskTitle",
                           (2, 5, 6, 2), lane_row_id="lane-1", lane_member_id="member-1")
    primitives = (mark, label)
    member = SceneLaneMember("lane-1", "member-1", ("mark-1", "label-1"), ("mark-1",))
    if broken == "inventory-omits-tagged":
        member = replace(member, emitted_primitive_ids=("mark-1",))
    elif broken == "inventory-mismatched-tags":
        primitives = (replace(mark, lane_member_id="other"), label)
    elif broken == "untagged-member-purpose":
        primitives = (mark, replace(label, lane_row_id=None, lane_member_id=None))
    elif broken == "unknown-primary-mark":
        member = replace(member, primary_mark_ids=("label-1",))
    elif broken.startswith("untagged-"):
        purpose = {
            "untagged-missing-actual": "missingActual",
            "untagged-progress-fill": "progress-fill",
            "untagged-summary-bar": "summary-bar",
        }[broken]
        extra = ScenePrimitive("extra", "Rect", "object", "object", purpose, purpose, (3, 3, 2, 2))
        primitives = (*primitives, extra)
    elif broken == "comparison-primary":
        actual = ScenePrimitive("actual", "Rect", "object", "object", "actual", "actual",
                                (2, 2, 4, 2), lane_row_id="lane-1", lane_member_id="member-1")
        primitives = (*primitives, actual)
        member = replace(member, emitted_primitive_ids=("mark-1", "label-1", "actual"),
                         primary_mark_ids=("actual",))

    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneSurface("s", (), (row,), (), None, primitives, lane_mode="lanes", lane_members=(member,))


def test_scene_serializer_does_not_reopen_layout_theme_or_renderer_policy():
    source = Path(__import__("chrona.presentation.scene.serialization", fromlist=["*"]).__file__).read_text(encoding="utf-8")
    assert "presentation.layout" not in source
    assert "presentation.renderers" not in source
    assert "theme_tokens" not in source


def test_render_review_reads_a_bound_summary_profile():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        assert closure.resource("summary-profile") is not None
        rendered = render_review(_request(closure, snapshot, require_all_inputs_read=True))
    assert "summary-profile" in rendered.read_inputs


def test_render_review_rejects_an_incomplete_closure():
    # An incomplete closure cannot be fabricated from arbitrary mappings.
    assert RenderRequest.__dataclass_fields__["closure"].type == "RenderClosure"


def test_render_review_is_deterministic_for_one_closure():
    with tempfile.TemporaryDirectory() as temporary:
        closure, snapshot = _closure(Path(temporary))
        first = render_review(_request(closure, snapshot))
        second = render_review(_request(closure, snapshot))
    assert first.artifact.content == second.artifact.content


def test_render_review_reports_a_theme_without_a_text_family():
    with tempfile.TemporaryDirectory() as temporary:
        closure, _snapshot = _closure(Path(temporary))
        with pytest.raises(TypeError):
            closure.resolved_theme.resolved_input["body"]["roles"]["text"].pop("fontFamily")
