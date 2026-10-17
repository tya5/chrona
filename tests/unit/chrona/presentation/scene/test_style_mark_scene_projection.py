from types import SimpleNamespace

from chrona.presentation.model.semantic_registry import (
    ContrastClass, PrimitiveKind, contrast_binding_for_primitive, semantic_binding,
)
from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import ScenePrimitive
from chrona.presentation.scene.v05_builder import _complete_primitive_paint, _mark_style_projection


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
    binding, projected = _mark_style_projection(mark, semantic_binding("planned"))

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
    binding, projected = _mark_style_projection(mark, semantic_binding("planned"))
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

    binding, projected = _mark_style_projection(mark, fallback)

    assert binding is fallback
    assert projected == {}
