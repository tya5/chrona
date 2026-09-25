from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding, contrast_bindings


def test_contrast_registry_classifies_only_the_finite_state_text_and_decoration_roles():
    assert [item.scene_role for item in contrast_bindings(ContrastClass.STATE_TEXT)] == [
        "variance-ahead", "variance-on-track", "variance-behind", "missing-actual-cell",
    ]
    assert [item.scene_role for item in contrast_bindings(ContrastClass.DECORATION)] == [
        "calendar-closed", "axis-band-decoration", "group-band", "row-band", "group-header-band",
    ]
    assert contrast_binding("text") is None
    assert contrast_binding("group-band").theme_role == "group-band"
