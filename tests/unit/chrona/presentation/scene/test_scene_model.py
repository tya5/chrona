import pytest

from chrona.presentation.scene.model import ScenePrimitive


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
