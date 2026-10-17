from types import SimpleNamespace
import pytest

from chrona.presentation.model.semantic_registry import (
    ContrastClass, PrimitiveKind, contrast_binding_for_primitive, semantic_binding,
)
from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive
from chrona.presentation.scene.v05_builder import _complete_primitive_paint, _placement_style_projection


def _tokens():
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "body": {
        "values": {
            "host-ink": {"type": "color", "value": "#112233"},
            "selected-ink": {"type": "color", "value": "#334455"},
        },
        "roles": {
            "planned": {"fill": "host-ink"},
            "style-plan": {"fill": "selected-ink"},
        },
    }})


def test_scene_projection_uses_exact_layout_occurrence_key_and_preserves_host_binding():
    key = StyleOccurrenceKey("task-17", "primary", "gate", "row-3", "member-2", occurrence_kind="row")
    mark = SimpleNamespace(placement_id="planned:row-3:member-2", theme_role="style-plan",
                           style_occurrence_key=key)
    binding, projected = _placement_style_projection(mark, semantic_binding("planned"))

    primitive = ScenePrimitive(
        mark.placement_id, PrimitiveKind.RECT, key.subject_id, "object",
        binding.purpose, binding.scene_role, (1.0, 2.0, 3.0, 3.0), **projected,
    )
    assert primitive.semantic_id == "gate"
    assert primitive.theme_role == "style-plan"
    assert primitive.purpose == "planned"
    assert primitive.visual_role == "gate"
    assert contrast_binding_for_primitive(primitive.visual_role, primitive.kind, primitive.purpose).contrast_class == ContrastClass.MARK


def test_completed_scene_paint_reads_selected_theme_role_without_changing_host_or_contrast():
    key = StyleOccurrenceKey("task-17", "primary", "planned", "row-3", "member-2", occurrence_kind="row")
    mark = SimpleNamespace(placement_id="planned:row-3:member-2", theme_role="style-plan",
                           style_occurrence_key=key)
    binding, projected = _placement_style_projection(mark, semantic_binding("planned"))
    primitive = ScenePrimitive(
        mark.placement_id, PrimitiveKind.RECT, key.subject_id, "object",
        binding.purpose, binding.scene_role, (1.0, 2.0, 3.0, 4.0), **projected,
    )

    completed, omissions = _complete_primitive_paint(primitive, _tokens(), None, None, {}, {})

    assert omissions == ()
    assert completed.paint.fill == "#334455"
    assert completed.visual_role == "planned" and completed.purpose == "planned"
    assert contrast_binding_for_primitive(completed.visual_role, completed.kind, completed.purpose).contrast_class == ContrastClass.MARK


def test_unstyled_scene_projection_keeps_legacy_binding_and_emits_no_style_metadata():
    fallback = semantic_binding("snapshot")
    mark = SimpleNamespace(placement_id="planned:task-17", theme_role=None, style_occurrence_key=None)

    binding, projected = _placement_style_projection(mark, fallback)

    assert binding is fallback
    assert projected == {}


@pytest.mark.parametrize("semantic_id", ("tableCell", "memberLabel", "varianceBehind"))
def test_text_projection_preserves_canonical_semantic_and_completes_selected_ink(semantic_id):
    key = StyleOccurrenceKey("task-17", "primary", semantic_id, "row-3", "member-2",
                             "Owner", occurrence_kind="table-cell")
    placed = SimpleNamespace(placement_id="text-17", theme_role="style-plan",
                             style_occurrence_key=key)
    binding, projected = _placement_style_projection(placed, None)
    primitive = ScenePrimitive(
        placed.placement_id, PrimitiveKind.TEXT, key.subject_id, "review",
        binding.purpose, binding.scene_role, (1.0, 2.0, 3.0, 4.0), **projected,
        table_row_id="row-3" if semantic_id == "tableCell" else None,
        table_column_id="Owner" if semantic_id == "tableCell" else None,
        contrast_treatment="required" if semantic_id == "varianceBehind" else None,
    )

    completed, omissions = _complete_primitive_paint(primitive, _tokens(), None, None, {}, {})

    assert omissions == ()
    assert completed.paint.fill == "#334455"
    assert completed.semantic_id == semantic_id
    assert completed.theme_role == "style-plan"
    assert completed.purpose == binding.purpose
    assert completed.visual_role == binding.scene_role
