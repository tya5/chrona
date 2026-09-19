import pytest

from chrona.gestures import propose_typed_field_gesture


def test_gesture_creates_only_a_stable_command_proposal():
    proposal = propose_typed_field_gesture("cmd-1", "revision-1", "object:task-1", "title", "Build")
    assert proposal.object_id == "task-1"
    assert proposal.base_revision == "revision-1"


def test_gesture_rejects_non_object_scene_targets():
    with pytest.raises(ValueError, match="E_GESTURE_TARGET"):
        propose_typed_field_gesture("cmd-1", "revision-1", "annotation:a", "title", "Build")
