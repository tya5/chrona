from datetime import date

import pytest

from chrona.presentation.contracts.resources import _compact_commands
from chrona.presentation.contracts.diagnostics import PresentationDiagnostic, PresentationIngressRejected
from chrona.presentation.fonts.importer import FontImportError, _axes, _numeric_advances, _outline_cap_height, _descriptor, import_font
from chrona.presentation.model.authoring import _apply_view_overrides, _declared_resource, AuthoringError
from chrona.presentation.model.info_diagnostics import PaintOmission, SuppressedPlotLabels
from chrona.presentation.model.semantic_realization import RealizationFamily, realization_family, validate_realization_families
from chrona.presentation.model.surface_content import display_value, _format_compact_date
from chrona.presentation.table_presentation import BooleanPresencePresentation
from chrona.schema_diagnostics import explain_all_errors, explain_errors


def test_authoring_resource_and_color_selection_diagnostics_name_requested_identity():
    with pytest.raises(AuthoringError, match="E_AUTHORING_PRESET_RESOURCE") as error:
        _declared_resource("theme", {"path": "themes/midnight.yaml", "id": "midnight"},
                           {"themes/midnight.yaml": {"id": "other", "kind": "theme"}})
    assert "slot='theme'" in str(error.value) and "expected kind/id='theme'/'midnight'" in str(error.value)


def test_authoring_override_body_diagnostic_names_actual_container_type():
    with pytest.raises(AuthoringError, match="E_AUTHORING_PRESET_RESOURCE") as error:
        _apply_view_overrides({"body": []}, {})
    assert "View body type=list" in str(error.value)
    assert "expected mutable mapping" in str(error.value)


def test_authoring_annotation_duplicate_diagnostic_names_repeated_identifier():
    view = {"body": {"annotations": [{"id": "note-1"}]}}
    additions = {"annotations": [
        {"id": "note-1", "anchor": {"object": "task-a"}},
        {"id": "note-2", "anchor": {"object": "task-b"}},
        {"id": "note-2", "anchor": {"object": "task-c"}},
    ]}
    with pytest.raises(AuthoringError, match="E_AUTHORING_ANNOTATION_ID") as error:
        _apply_view_overrides(view, additions)
    assert "duplicate annotation ids=('note-1', 'note-2')" in str(error.value)


@pytest.mark.parametrize(("value", "formatter", "operand"), [
    (True, "text", "valueType=bool"),
    (42, BooleanPresencePresentation("yes", "no"), "valueType=int"),
])
def test_boolean_presentation_diagnostic_names_value_and_formatter(value, formatter, operand):
    with pytest.raises(ValueError, match="E_VIEW_BOOLEAN_PRESENTATION") as error:
        display_value(value, "blank", formatter)
    assert operand in str(error.value)


def test_locale_diagnostic_names_unsupported_locale_and_allowed_alternatives():
    with pytest.raises(ValueError, match="E_PRESENTATION_LOCALE_UNSUPPORTED") as error:
        _format_compact_date(date(2026, 1, 2), include_year=True, locale="fr-FR")
    assert "locale='fr-FR'" in str(error.value) and "('en-US', 'ja-JP')" in str(error.value)


def test_presentation_info_errors_name_offending_fields_and_operand_values():
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID") as labels:
        SuppressedPlotLabels("timeline;primary", 0)
    assert "surfaceId='timeline;primary'" in str(labels.value) and "count=0" in str(labels.value)

    assert "surfaceId='timeline;primary'" in str(labels.value) and "count=0" in str(labels.value)


def test_paint_omission_diagnostic_names_invalid_treatment_operand():
    with pytest.raises(ValueError, match="E_PRESENTATION_INFO_INVALID") as omission:
        PaintOmission("text", "unknown-effect", "/body/roles/text", "screen", "svg", None)
    assert "treatment" in str(omission.value) and "unknown-effect" in str(omission.value)


def test_realization_diagnostic_names_duplicate_family_fields():
    with pytest.raises(ValueError, match="E_PRESENTATION_REALIZATION_INVALID") as invalid:
        validate_realization_families((RealizationFamily("family-delta", "selector", "cell", ("ready", "ready")),))
    assert "familyId='family-delta'" in str(invalid.value)
    assert "expected unique id" in str(invalid.value)


def test_realization_diagnostic_names_unadmitted_equivalence_state():
    with pytest.raises(ValueError, match="E_PRESENTATION_REALIZATION_INVALID") as bad_equivalence:
        validate_realization_families((RealizationFamily("family-epsilon", "selector", "cell", ("ready",), (("missing", "intentional"),)),))
    assert "familyId='family-epsilon', equivalenceState='missing'" in str(bad_equivalence.value)
    assert "expected admitted state" in str(bad_equivalence.value)


def test_unknown_realization_diagnostic_names_requested_identifier_and_alternatives():
    with pytest.raises(ValueError, match="E_PRESENTATION_REALIZATION_UNKNOWN") as unknown:
        realization_family("annotation-purpose-v2")
    assert "identifier='annotation-purpose-v2'" in str(unknown.value)
    assert "annotation-purpose" in str(unknown.value)


@pytest.mark.parametrize("explain", [explain_errors, explain_all_errors])
def test_empty_schema_explanation_diagnostic_names_empty_operand(explain):
    with pytest.raises(ValueError, match="E_SCHEMA_VIOLATION_EMPTY") as error:
        explain(())
    assert "0" in str(error.value) and "expected one or more schema validation errors" in str(error.value)


def test_presentation_ingress_rejection_detail_names_count_and_distinct_codes():
    error = PresentationIngressRejected((
        PresentationDiagnostic("E_VIEW", "view", "board", "/body", None, "invalid", "schema"),
        PresentationDiagnostic("E_VIEW", "view", "board", "/body/title", None, "invalid", "schema"),
        PresentationDiagnostic("E_THEME", "theme", "night", "/body", None, "invalid", "schema"),
    ))
    assert str(error) == "E_PRESENTATION_REJECTED"
    assert "diagnosticCount=3" in error.detail
    assert "codes=('E_VIEW', 'E_THEME')" in error.detail


@pytest.mark.parametrize(("commands", "operand"), [
    (None, "command stream type=NoneType"),
    ("X 4 5", "command='X'"),
    ("M nope 1", "coordinate='nope'"),
    ("L 1 2", "first command='line'"),
])
def test_icon_geometry_contract_diagnostic_names_invalid_command_operand(commands, operand):
    with pytest.raises(ValueError, match="E_ICON_CATALOG_GEOMETRY") as error:
        _compact_commands(commands)
    assert operand in error.value.detail


def test_font_axis_diagnostic_names_bad_assignment_operand():
    with pytest.raises(FontImportError, match="E_FONT_IMPORT_AXIS") as error:
        _axes(("wght=wide",))
    assert "assignment='wght=wide'" in error.value.detail
    assert "four-character axis tag=value" in error.value.detail


def test_font_argument_diagnostic_names_invalid_weight_and_family():
    from pathlib import Path
    with pytest.raises(FontImportError, match="E_FONT_IMPORT_ARGUMENT") as error:
        import_font(Path("absent.ttf"), Path("unused"), family=" ", weight=1201)
    assert "familyPresent=False, weight=1201" in error.value.detail
    assert "weight 1..1000" in error.value.detail


def test_font_missing_source_diagnostic_names_read_failure_type_and_face_index(tmp_path):
    missing = tmp_path / "missing-face-17.ttf"
    with pytest.raises(FontImportError, match="E_FONT_IMPORT_INPUT") as error:
        import_font(missing, tmp_path / "out", family="Test Sans", weight=400, index=3)
    assert error.value.source_ref == "/source"
    assert "sourceReadOrFaceSelectionError=FileNotFoundError" in error.value.detail
    assert "collectionIndex=3" in error.value.detail
    assert "expected readable font face" in error.value.detail


def test_font_numeric_advance_diagnostic_names_digit_operand_and_expected_metric():
    class Font(dict):
        pass
    cmap = {ord(str(digit)): f"digit{digit}" for digit in range(10)}
    hmtx = {glyph: (index + 1, 0) for index, glyph in enumerate(cmap.values())}
    with pytest.raises(FontImportError, match="E_FONT_IMPORT_FORMAT") as error:
        _numeric_advances(Font(), cmap, hmtx)
    assert error.value.source_ref == "/numericAdvances/tabular"
    assert "distinctAdvanceCount=10" in error.value.detail
    assert "one shared tabular advance" in error.value.detail


def test_font_cap_height_diagnostic_names_missing_glyph_operand():
    with pytest.raises(FontImportError, match="E_FONT_CAP_HEIGHT_REQUIRED") as error:
        _outline_cap_height(object(), {}, 1000)
    assert error.value.source_ref == "/cmap/H"
    assert "uppercase H has no cmap glyph" in error.value.detail


def test_font_descriptor_diagnostic_names_invalid_descriptor_shape(tmp_path):
    path = tmp_path / "font-metrics.yaml"
    path.write_text("algorithm: wrong\nassets: []\n", encoding="utf-8")
    with pytest.raises(FontImportError, match="E_FONT_IMPORT_DESCRIPTOR") as error:
        _descriptor(path)
    assert error.value.source_ref == "/font-metrics.yaml"
    assert "algorithm='wrong'" in error.value.detail
    assert "declared-metrics-v3" in error.value.detail
