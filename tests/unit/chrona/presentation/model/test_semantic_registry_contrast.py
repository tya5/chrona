import pytest

from chrona.presentation.model.semantic_registry import (
    ContrastClass, contrast_binding, contrast_binding_for, contrast_bindings, semantic_binding, semantic_ids,
)

# Free ink on a ground the Theme chose (#884, #980): every Text a surface draws that no role-classified binding covers.
GROUND_TEXT_SEMANTICS = {
    "groupHeader", "asOfLabel", "axisBand", "axisLabel", "axisLabel2", "axisLabel3", "groupDetail", "titleText",
    "subtitleText", "kickerText", "tableColumnLabel", "tableCell", "memberLabel", "memberLabelInsidePlanned",
    "memberLabelInsideActual", "memberLabelInsideSnapshot", "memberLabelInsideScenario", "milestoneDigestEntry",
    "relationLabel", "legendLabel", "projectNote", "noteIndex", "annotationCalloutText", "annotationHighlightText",
    "annotationArrowText", "summaryHeader", "summaryMetric", "summaryFigureValue", "summaryFigureCaption",
    "summaryCaption", "summaryUnit",
    "slotHeading", "annotationListText", "networkLabel", "observationSource", "observationColumnLabel",
    "observationCell",
}
# Labels painted in the role of a classified state text: the classification is by that role, not by their own.
LABELS_CLASSIFIED_BY_ROLE = {"finishDelta", "varianceAhead", "varianceBehind",
                             "observationAttentionCell", "observationCriticalCell"}


def test_contrast_registry_classifies_only_the_finite_state_text_and_decoration_roles():
    assert [item.scene_role for item in contrast_bindings(ContrastClass.STATE_TEXT)] == [
        "period-label", "variance-ahead", "variance-on-track", "variance-behind", "missing-actual-cell",
        "annotation-note-text", "annotation-kind-label", "annotation-kind-secondary", "annotation-heading",
    ]
    assert [item.scene_role for item in contrast_bindings(ContrastClass.DECORATION)] == [
        "calendar-closed", "calendar-exception", "period-band", "axis-band-decoration", "axis-band-decoration2",
        "group-band", "row-band", "row-rule", "group-header-band", "group-header-strip", "group-tab", "annotation-note-box",
        "annotation-kind-bar", "annotation-kind-accent", "annotation-kind-stamp", "annotation-artwork",
        "annotation-border-start", "annotation-border-end", "annotation-border-top", "annotation-border-bottom",
    ]
    assert {item.semantic_id for item in contrast_bindings(ContrastClass.GROUND_TEXT)} == GROUND_TEXT_SEMANTICS
    assert contrast_binding("text") is None
    assert contrast_binding("group-band").theme_role == "group-band"


def test_member_label_is_retained_as_text_and_member_leader_semantic_is_retired():
    assert "memberLabelLeader" not in semantic_ids()
    assert semantic_binding("memberLabel").primitive_kind == "label"
    assert semantic_binding("annotationCalloutLeader").purpose == "annotation-leader"
    with pytest.raises(ValueError, match="E_PRESENTATION_SEMANTIC_UNKNOWN"):
        semantic_binding("memberLabelLeader")


def test_network_node_labels_keep_shared_ink_and_existing_public_purpose():
    label = semantic_binding("networkLabel")
    title = semantic_binding("titleText")
    assert label.purpose == title.purpose == "title-text"
    assert label.scene_role == label.theme_role == "text"
    assert title.scene_role == "heading"
    assert contrast_binding_for(label.scene_role, label.purpose).contrast_class == ContrastClass.GROUND_TEXT


def test_every_label_semantic_is_classified_so_a_new_label_cannot_reopen_the_hole():
    unclassified = {
        item.semantic_id for item in (semantic_binding(name) for name in semantic_ids())
        if item.primitive_kind == "label" and item.contrast_class is None
    }
    assert unclassified == LABELS_CLASSIFIED_BY_ROLE
    for name in LABELS_CLASSIFIED_BY_ROLE:
        item = semantic_binding(name)
        assert contrast_binding(item.scene_role) is not None and contrast_binding(item.scene_role).contrast_class in (
            ContrastClass.STATE_TEXT,), name


def test_free_text_resolves_by_purpose_in_the_shared_role_and_by_role_and_purpose_in_its_own():
    for purpose in ("as-of-label", "member-label", "axis-label", "table-cell", "legend-label", "group-detail",
                    "annotation-list-text"):
        assert contrast_binding_for("text", purpose).contrast_class == ContrastClass.GROUND_TEXT, purpose
    for role, purpose in (("axis-label2", "axis-label"), ("axis-label3", "axis-label"),
                          ("member-label-inside-planned", "member-label"), ("note-index", "note-index"),
                          ("annotation-callout-text", "annotation-text"), ("metric", "summary-figure-value"),
                          ("slot-heading", "slot-heading"), ("heading", "title-text"),
                          ("subtitle", "subtitle-text"), ("kicker", "kicker-text"),
                          ("text", "title-text"), ("text", "subtitle-text"), ("text", "kicker-text")):
        assert contrast_binding_for(role, purpose).contrast_class == ContrastClass.GROUND_TEXT, (role, purpose)
    # A role of its own never borrows another purpose's class, and only a Text primitive (a purpose) can be ground text.
    assert contrast_binding_for("axis-label2", "member-label") is None
    assert contrast_binding_for("text", None) is None and contrast_binding_for("axis-label2", None) is None
    assert contrast_binding_for("text", "no-such-purpose") is None
    # A role classified by its own class wins over the purpose.
    assert contrast_binding_for("variance-behind", "axis-label").contrast_class == ContrastClass.STATE_TEXT


def test_a_theme_text_paint_role_is_ground_text_by_its_purpose(tmp_path):
    """The header role, the legend role and a View-named column role are judged like `text` (#1062)."""
    for role, purpose in (("tableColumnLabel", "table-column-label"), ("legend", "legend-label"),
                          ("table-cell-secondary", "table-cell"), ("heading", "table-cell"),
                          ("subtitle", "table-cell"), ("kicker", "table-cell")):
        assert contrast_binding_for(role, purpose).contrast_class == ContrastClass.GROUND_TEXT, (role, purpose)
    # The purpose still decides: a named role on a purpose no ground-text binding owns, or on no purpose, is not classified,
    # and a registered role never borrows another purpose's class.
    assert contrast_binding_for("table-cell-secondary", "no-such-purpose") is None
    assert contrast_binding_for("table-cell-secondary", None) is None
    assert contrast_binding_for("axis-label2", "member-label") is None
