import pytest

from chrona.presentation.model.semantic_registry import (
    ContrastClass, contrast_binding, contrast_bindings, semantic_binding, semantic_ids,
)


def test_contrast_registry_classifies_only_the_finite_state_text_and_decoration_roles():
    assert [item.scene_role for item in contrast_bindings(ContrastClass.STATE_TEXT)] == [
        "period-label", "variance-ahead", "variance-on-track", "variance-behind", "missing-actual-cell",
        "annotation-note-text", "annotation-kind-label", "annotation-kind-secondary",
    ]
    assert [item.scene_role for item in contrast_bindings(ContrastClass.DECORATION)] == [
        "calendar-closed", "period-band", "axis-band-decoration", "axis-band-decoration2",
        "group-band", "row-band", "group-header-band", "annotation-note-box",
        "annotation-kind-bar", "annotation-kind-accent",
    ]
    assert contrast_binding("text") is None
    assert contrast_binding("group-band").theme_role == "group-band"


def test_member_label_is_retained_as_text_and_member_leader_semantic_is_retired():
    assert "memberLabelLeader" not in semantic_ids()
    assert semantic_binding("memberLabel").primitive_kind == "label"
    assert semantic_binding("annotationCalloutLeader").purpose == "annotation-leader"
    with pytest.raises(ValueError, match="E_PRESENTATION_SEMANTIC_UNKNOWN"):
        semantic_binding("memberLabelLeader")
