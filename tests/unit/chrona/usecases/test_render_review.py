"""The render use case is callable with a closure, without a command line."""
from __future__ import annotations

import tempfile
import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import jsonschema

import chrona.usecases.render_review as render_usecase
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.contracts.resources import ViewLaneLabel, ViewLaneTable, ViewRowMode
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


def test_lane_source_measurement_uses_finite_table_envelope_and_seed_block():
    items = (SimpleNamespace(title="Long candidate title", group_label="Avionics"),
             SimpleNamespace(title="Short", group_label="Avionics"))
    projection = SimpleNamespace(
        rows=(SimpleNamespace(row_id="row", group_id="g", label="row", items=items),),
        items=items, window=(date(2026, 1, 1), date(2026, 1, 31)), network=None,
    )
    view = SimpleNamespace(
        rows=SimpleNamespace(mode=ViewRowMode.LANES,
                             lane_table=ViewLaneTable(ViewLaneLabel.GROUP, True)),
        table_columns=(),
    )
    sources = render_usecase._source_inputs(
        {"project": {"title": "test"}}, view, projection, SimpleNamespace(runs=()),
    )

    assert sources["table"].item_count == sources["timeline"].item_count == 1
    assert tuple(column.column_id for column in sources["table"].table.columns) == ("Lane", "Items")
    assert {cell.content for cell in sources["table"].table.cells} == {
        "Avionics", "Long candidate title", "Short", "2",
    }


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


def _closure(temporary: Path):
    snapshot = temporary / "snapshot"
    snapshot.mkdir()
    reference, _ = _copy_context_closure(EXAMPLE.resolve(), EXAMPLE / "contexts/02-programme-board.yaml", snapshot)
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
