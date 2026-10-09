import pytest

from chrona.presentation.color_scheme import ColorSchemeError, resolve_color_scheme, resolve_theme


def scheme():
    return {"version": "chrona/color-scheme/v0.2", "kind": "color-scheme", "body": {"colors": {"surface": "#FFFFFF", "surfaceRaised": "#F5F7FA", "text": "#172033", "textMuted": "#4B5563", "accent": "#1D4ED8", "positive": "#047857", "negative": "#B91C1C", "warning": "#A16207", "neutral": "#475569", "insideLabelPlanned": "#FFFFFF", "insideLabelActual": "#FFFFFF", "insideLabelSnapshot": "#FFFFFF", "insideLabelScenario": "#FFFFFF"}, "categories": {"team-a": "#123456", "team-b": "#654321"}, "provenance": {"kind": "chrona-authored", "source": "test", "license": "pending"}}}


def test_scheme_requires_provenance_and_resolves_named_categories():
    value = resolve_color_scheme(scheme(), content_identity="sha256:" + "a" * 64)
    assert value["category:team-a"] == "#123456"
    del scheme()["body"]["provenance"]
    bad = scheme(); del bad["body"]["provenance"]
    with pytest.raises(ColorSchemeError, match="E_SCHEME_PROVENANCE"):
        resolve_color_scheme(bad, content_identity="sha256:" + "a" * 64)


def test_scheme_rejects_insufficient_text_contrast():
    bad = scheme(); bad["body"]["colors"]["text"] = "#F5F7FA"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_CONTRAST") as error:
        resolve_color_scheme(bad, content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colors/text"
    assert "4.5:1 against surface and surfaceRaised" in error.value.detail


def test_theme_validates_each_inside_label_role_against_its_host_mark():
    theme = {"version": "chrona/theme/v0.15", "kind": "theme", "id": "inside", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "planned.fill": "accent", "actual.fill": "positive", "snapshot.fill": "neutral",
            "variance-ahead.fill": "positive", "variance-on-track.fill": "textMuted",
            "variance-behind.fill": "negative", "missing-actual-cell.fill": "textMuted",
            "member-label-inside-planned.fill": "insideLabelPlanned",
            "member-label-inside-actual.fill": "insideLabelActual",
            "member-label-inside-snapshot.fill": "insideLabelSnapshot",
            "member-label-inside-scenario.fill": "insideLabelScenario",
        }, "metrics": {},
    }}
    resolved = resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert "member-label-inside-planned" in resolved["body"]["roles"]
    theme["body"]["colorBindings"]["member-label-inside-planned.fill"] = "accent"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_INSIDE_LABEL_CONTRAST") as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.source_ref == "/body/colorBindings/member-label-inside-planned.fill"
    assert "intent='accent'" in error.value.detail and "expected insideLabelPlanned" in error.value.detail


def test_theme_state_text_requires_declared_treatment_and_composited_floor():
    theme = {"version": "chrona/theme/v0.15", "kind": "theme", "id": "state", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "variance-ahead.fill": "positive", "variance-on-track.fill": "textMuted",
            "variance-behind.fill": "negative", "missing-actual-cell.fill": "textMuted",
        }, "metrics": {},
    }}
    resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    theme["body"]["roles"]["variance-behind"]["contrastTreatment"] = "deemphasized"
    with pytest.raises(ColorSchemeError, match="E_SCHEME_STATE_TEXT_TREATMENT"):
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    theme["body"]["roles"]["variance-behind"]["contrastTreatment"] = "required"
    del theme["body"]["roles"]["variance-ahead"]["contrastTreatment"]
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_TREATMENT"
    assert error.value.source_ref == "/body/roles/variance-ahead"
    assert "role='variance-ahead', treatment=None" in error.value.detail
    assert "expected required or deemphasized" in error.value.detail


def _note_theme():
    theme = {"version": "chrona/theme/v0.15", "kind": "theme", "id": "note", "body": {
        "values": {}, "roles": {
            "variance-ahead": {"contrastTreatment": "deemphasized"},
            "variance-on-track": {"contrastTreatment": "required"},
            "variance-behind": {"contrastTreatment": "required"},
            "missing-actual-cell": {"contrastTreatment": "required"},
            "annotation-note-box": {},
            "annotation-note-text": {"contrastTreatment": "required"},
        }, "colorBindings": {
            "variance-ahead.fill": "positive",
            "variance-on-track.fill": "textMuted",
            "variance-behind.fill": "negative",
            "missing-actual-cell.fill": "textMuted",
            "annotation-note-box.fill": "surfaceRaised",
            "annotation-note-text.fill": "text",
        }, "metrics": {},
    }}
    return theme


def test_annotation_note_text_requires_required_treatment():
    theme = _note_theme()
    theme["body"]["roles"]["annotation-note-text"]["contrastTreatment"] = "deemphasized"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_TREATMENT"
    assert error.value.source_ref == "/body/roles/annotation-note-text/contrastTreatment"
    assert "role='annotation-note-text', treatment='deemphasized'" in error.value.detail


def test_annotation_note_box_requires_effective_flat_opaque_fill():
    theme = _note_theme()
    theme["body"]["colorBindings"].pop("annotation-note-box.fill")
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/roles/annotation-note-box/fill"
    assert "role='annotation-note-box'" in error.value.detail
    assert "expected opaque #RRGGBB color token" in error.value.detail

    theme = _note_theme()
    theme["body"]["roles"]["annotation-note-box"]["opacity"] = "note-opacity"
    theme["body"]["values"]["note-opacity"] = {"type": "number", "value": 0.5}
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/roles/annotation-note-box/opacity"
    assert "token='note-opacity'" in error.value.detail and "expected opacity 1" in error.value.detail


def test_annotation_note_box_accepts_scheme_inserted_opaque_fill_and_default_opacity():
    resolved = resolve_theme(_note_theme(), scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert resolved["body"]["roles"]["annotation-note-box"]["fill"].startswith("__scheme.surfaceRaised.")


def test_annotation_note_box_rejects_gradient_or_pattern_ground_with_exact_pointer():
    theme = _note_theme()
    theme["body"]["colorBindings"]["annotation-note-box.gradientStart"] = "accent"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/colorBindings/annotation-note-box.gradientStart"
    assert "property='gradientStart'" in error.value.detail

    theme = _note_theme()
    theme["body"]["roles"]["annotation-note-box"]["pattern"] = "box-pattern"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity="sha256:" + "a" * 64)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"
    assert error.value.source_ref == "/body/roles/annotation-note-box/pattern"


# #950: note ink is judged on the note box it lies on, not on the canvas it floats above.
IDENTITY = "sha256:" + "a" * 64


def _dark_scheme(**colors):
    value = scheme()
    value["body"]["colors"].update({"surface": "#101820", "surfaceRaised": "#1B2733", "text": "#F2EBDD",
                                    "textMuted": "#C9C1B0", "accent": "#7FB2E5"})
    value["body"]["colors"].update(colors)
    return value


def _paper_note_theme(box="text", ink="surface"):
    """A dark-first Theme with paper notes: the box fill is a light intent, the ink a dark one."""
    theme = _note_theme()
    theme["body"]["colorBindings"].update({
        "annotation-note-box.fill": box, "annotation-note-text.fill": ink,
        "variance-ahead.fill": "text", "variance-on-track.fill": "textMuted",
        "variance-behind.fill": "accent", "missing-actual-cell.fill": "textMuted"})
    return theme


def test_dark_ink_on_a_light_note_box_over_a_dark_canvas_resolves():
    resolved = resolve_theme(_paper_note_theme(), _dark_scheme(), scheme_content_identity=IDENTITY)
    roles = resolved["body"]["roles"]
    assert roles["annotation-note-box"]["fill"].startswith("__scheme.text.")
    assert roles["annotation-note-text"]["fill"].startswith("__scheme.surface.")


def test_note_ink_too_close_to_its_box_fails_naming_the_role_and_the_box():
    # The ink contrasts the dark canvas well; it is the light box it lies on that it cannot be read against.
    theme = _paper_note_theme(box="text", ink="textMuted")
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_CONTRAST"
    assert error.value.source_ref == "/body/roles/annotation-note-text/fill"
    assert error.value.detail.startswith("'annotation-note-text':'annotation-note-box':")


def test_note_ink_that_reads_on_the_canvas_but_not_on_its_box_fails():
    # Light ink passes the dark canvas (the old rule) and fails the light box it is drawn on.
    theme = _paper_note_theme(box="text", ink="text")
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert error.value.detail.startswith("'annotation-note-text':'annotation-note-box':")


def test_light_canvas_notes_resolve_as_before_and_a_dark_box_needs_a_light_ink():
    resolve_theme(_note_theme(), scheme(), scheme_content_identity=IDENTITY)
    theme = _note_theme()
    theme["body"]["colorBindings"]["annotation-note-box.fill"] = "accent"
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, scheme(), scheme_content_identity=IDENTITY)
    assert error.value.detail.startswith("'annotation-note-text':'annotation-note-box':")


def test_note_ink_opacity_counts_against_the_box():
    theme = _paper_note_theme()
    theme["body"]["roles"]["annotation-note-text"]["opacity"] = "ink-opacity"
    theme["body"]["values"]["ink-opacity"] = {"type": "number", "value": 0.25}
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert error.value.detail.startswith("'annotation-note-text':'annotation-note-box':")


def test_a_note_box_with_no_readable_fill_leaves_the_canvas_as_the_ground():
    # Without a box colour the canvas is the only ground there is: ink invisible on it is still the contrast error,
    # and ink readable on it reaches the note-ground check, which names the box.
    theme = _paper_note_theme(ink="surface")
    theme["body"]["colorBindings"].pop("annotation-note-box.fill")
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_CONTRAST"
    assert error.value.detail.startswith("'annotation-note-text':")
    assert "annotation-note-box" not in error.value.detail
    theme = _paper_note_theme(ink="text")
    theme["body"]["colorBindings"].pop("annotation-note-box.fill")
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert error.value.diagnostic_id == "E_SCHEME_ANNOTATION_NOTE_GROUND"


def test_only_the_note_box_is_the_ground_of_note_ink():
    # A dark callout box never carries note prose: it is not a ground for it.
    theme = _paper_note_theme()
    theme["body"]["roles"]["annotation-callout-box"] = {}
    theme["body"]["colorBindings"]["annotation-callout-box.fill"] = "surface"
    resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)


# --- #995: the decoration severity knob --------------------------------------------------------------------


def test_the_contrast_policy_is_carried_into_the_resolved_theme_and_absent_when_undeclared():
    theme = _paper_note_theme()
    assert "contrastPolicy" not in resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)["body"]
    for severity in ("warning", "error"):
        theme["body"]["contrastPolicy"] = {"decoration": severity}
        resolved = resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
        assert resolved["body"]["contrastPolicy"] == {"decoration": severity}


@pytest.mark.parametrize("policy,pointer", [
    ({"decoration": "info"}, "/body/contrastPolicy/decoration"),
    ({"mark": False}, "/body/contrastPolicy/mark"),  # YAML 1.1 reads an unquoted `off` as false
    ({"decoration": "error", "marks": "warning"}, "/body/contrastPolicy/marks"),
    ({"stateText": "strict"}, "/body/contrastPolicy/stateText"),
    ("error", "/body/contrastPolicy")])
def test_an_undeclared_policy_value_or_member_is_refused_at_its_pointer(policy, pointer):
    theme = _paper_note_theme()
    theme["body"]["contrastPolicy"] = policy
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert (error.value.diagnostic_id, error.value.source_ref) == ("E_THEME_CONTRAST_POLICY", pointer)


@pytest.mark.parametrize("member", ["mark", "stateText", "groundText", "decoration", "unsupportedGround"])
@pytest.mark.parametrize("severity", ["none", "warning", "error"])
def test_every_policy_member_accepts_none_warning_and_error(member, severity):
    theme = _paper_note_theme()
    theme["body"]["contrastPolicy"] = {member: severity}
    resolved = resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert resolved["body"]["contrastPolicy"] == {member: severity}


def test_an_empty_policy_declares_nothing():
    theme = _paper_note_theme()
    theme["body"]["contrastPolicy"] = {}
    assert "contrastPolicy" not in resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)["body"]


@pytest.mark.parametrize("policy", [None, {"decoration": "warning"}, {"decoration": "error"},
                                    {"stateText": "none"}, {"stateText": "warning"}])
def test_the_policy_never_softens_a_text_check_at_theme_resolution(policy):
    # Theme resolution holds the Theme's own static text checks; they are not contrast constraints of the gate.
    theme = _paper_note_theme(box="text", ink="textMuted")  # note ink too close to its box: the state-text error
    if policy is not None:
        theme["body"]["contrastPolicy"] = policy
    with pytest.raises(ColorSchemeError) as error:
        resolve_theme(theme, _dark_scheme(), scheme_content_identity=IDENTITY)
    assert error.value.diagnostic_id == "E_SCHEME_STATE_TEXT_CONTRAST"


# --- #991: the optional `rule` intent --------------------------------------------------------------------------


def _line_theme(binding: str) -> dict:
    return {"version": "chrona/theme/v0.15", "kind": "theme", "id": "lines", "body": {
        "values": {"w": {"type": "number", "value": 1}},
        "roles": {"axis-rule": {"strokeWidth": "w"}, "variance-ahead": {"contrastTreatment": "deemphasized"},
                  "variance-on-track": {"contrastTreatment": "required"},
                  "variance-behind": {"contrastTreatment": "required"},
                  "missing-actual-cell": {"contrastTreatment": "required"}},
        "colorBindings": {"axis-rule.stroke": binding, "variance-ahead.fill": "positive", "variance-on-track.fill": "textMuted",
                          "variance-behind.fill": "negative", "missing-actual-cell.fill": "textMuted"},
        "metrics": {}}}


def test_an_optional_rule_intent_binds_a_line_colour():
    declared = scheme()
    declared["body"]["colors"]["rule"] = "#C9CED6"
    resolved = resolve_theme(_line_theme("rule"), declared, scheme_content_identity="sha256:" + "a" * 64)
    token = resolved["body"]["roles"]["axis-rule"]["stroke"]
    assert resolved["body"]["values"][token]["value"] == "#C9CED6"


def test_a_scheme_without_rule_still_resolves_and_binding_rule_to_it_is_a_typed_error():
    assert "rule" not in resolve_color_scheme(scheme(), content_identity="sha256:" + "a" * 64)
    resolve_theme(_line_theme("text"), scheme(), scheme_content_identity="sha256:" + "a" * 64)  # a Theme not using it
    with pytest.raises(ColorSchemeError, match="E_SCHEME_INTENT_UNKNOWN"):
        resolve_theme(_line_theme("rule"), scheme(), scheme_content_identity="sha256:" + "a" * 64)


def test_the_rule_colour_is_not_a_contrast_surface():
    declared = scheme()
    declared["body"]["colors"]["rule"] = "#FFFFFF"  # as light as the canvas: a hairline, never judged as text
    assert resolve_color_scheme(declared, content_identity="sha256:" + "a" * 64)["rule"] == "#FFFFFF"
