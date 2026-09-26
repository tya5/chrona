"""The render use case is callable with a closure, without a command line."""
from __future__ import annotations

import tempfile
import json
from pathlib import Path

import pytest

import chrona.usecases.render_review as render_usecase
from chrona.presentation.layout.model import LayoutError
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
from chrona.presentation.scene.serialization import SceneSerializationError, scene_document, serialize_scene, validate_scene_document


def test_font_substitution_warning_only_claims_raster_draw_result():
    substitution = FontGlyphSubstitution("Requested", "Metrics only", 400, 0x2705, "✅")
    assert _font_warnings((substitution,), "png")[0].drawn is False
    assert _font_warnings((substitution,), "pdf")[0].drawn is False
    assert _font_warnings((substitution,), "svg")[0].drawn is None


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
