import pytest

from chrona.presentation.scene.model import (
    SceneLaneObstacle, SceneLaneRectObstacle, ScenePrimitive, SceneSurface,
)


@pytest.mark.parametrize("treatment", [None, "deemphasized", "other"])
def test_typed_note_text_requires_required_contrast_treatment(treatment):
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(
            "note-text", "Text", "note:1", "annotation", "annotation-note-text",
            "annotation-note-text", (0, 0, 20, 10), contrast_treatment=treatment,
        )


def test_typed_note_text_accepts_required_contrast_treatment():
    ScenePrimitive(
        "note-text", "Text", "note:1", "annotation", "annotation-note-text",
        "annotation-note-text", (0, 0, 20, 10), contrast_treatment="required",
    )


def test_other_state_text_keeps_deemphasized_treatment():
    ScenePrimitive(
        "variance", "Text", "task:1", "task", "variance-ahead", "variance-ahead",
        (0, 0, 20, 10), contrast_treatment="deemphasized",
    )


def test_lane_obstacles_reject_retired_member_leader_route_class():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneLaneObstacle("facet", "leader", "lane", "member", "leader-route",
                          SceneLaneRectObstacle(0, 0, 1, 1))


def test_scene_v06_and_v07_lane_obstacle_schemas_reject_leader_route():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[5]
    for version in ("0.6", "0.7"):
        schema = yaml.safe_load((root / f"schemas/scene-v{version}.schema.yaml").read_text(encoding="utf-8"))
        obstacle_classes = schema["$defs"]["laneObstacle"]["properties"]["class"]["enum"]
        assert obstacle_classes == ["mark", "required-label"]


def test_ordinary_scene_text_can_keep_its_exact_completed_host():
    host = ScenePrimitive("mark", "Rect", "item", "object", "planned", "planned",
                          (0, 0, 4, 4), slot_id="timeline", paint_order=1)
    text = ScenePrimitive("label", "Text", "item", "object", "member-label", "text",
                          (5, 0, 20, 4), slot_id="timeline", paint_order=2,
                          host_placement_id="mark")

    SceneSurface("surface", (), (), (), None, (host, text))
