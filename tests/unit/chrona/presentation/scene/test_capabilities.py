import pytest

from chrona.presentation.scene.capabilities import (
    CapabilityDisposition,
    LINEAR_GRADIENT,
    admitted_capability_ids,
    capability_ceiling,
    theme_catalog_pattern_consumer,
    theme_role_property_consumer,
    theme_catalog_pattern_consumer,
    theme_role_contract,
    validate_substitution_request,
)


def test_capability_ceiling_records_every_disposition_and_runtime_id_is_admitted():
    ceiling = capability_ceiling()
    assert {item.disposition for item in ceiling} == set(CapabilityDisposition)
    assert all(item.identifier != "member-label-leader" for item in ceiling)
    assert LINEAR_GRADIENT in admitted_capability_ids(LINEAR_GRADIENT)
    with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_CEILING"):
        admitted_capability_ids("decoration.row-band")


def test_substitution_requires_a_capability_specific_semantic_owner():
    with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_SUBSTITUTION"):
        validate_substitution_request(LINEAR_GRADIENT)


def test_catalogue_pattern_contract_admits_only_always_rect_roles():
    allowed = {
        "missing-actual", "network-node", "progress-fill", "summary-bar",
        "annotation-highlight-box", "axis-band-decoration", "axis-band-decoration2",
        "as-of-label-chip", "member-label-chip", "finish-delta-chip",
    }
    assert all(theme_catalog_pattern_consumer(role, "pattern") is not None for role in allowed)
    assert theme_catalog_pattern_consumer("planned", "pattern") is None
    assert theme_catalog_pattern_consumer("actual", "pattern") is None
    assert theme_catalog_pattern_consumer("snapshot", "pattern") is None
    assert theme_catalog_pattern_consumer("scenario", "pattern") is None
    assert theme_catalog_pattern_consumer("milestone", "pattern") is None
    assert theme_catalog_pattern_consumer("annotation-callout-box", "pattern") is None
    assert theme_catalog_pattern_consumer("annotation-arrow-box", "pattern") is None
    assert theme_catalog_pattern_consumer("annotation-note-box", "pattern") is None
    # This restriction is specific to new catalogue values. Existing Theme
    # applicability for legacy patterns remains unchanged.
    assert theme_role_property_consumer("planned", "pattern") is not None


def test_period_variant_roles_have_only_their_registered_capability_contracts():
    band = theme_role_contract("period-band:frost")
    label = theme_role_contract("period-label:frost")
    assert band is not None and band.scene_kinds == frozenset(("Rect", "Path"))
    assert label is not None and label.scene_kinds == frozenset(("Text",))
    assert theme_role_property_consumer("period-band:frost", "backgroundPaintOrder") is not None
    assert theme_role_property_consumer("period-band:frost", "edgeRules") is not None
    assert theme_role_property_consumer("period-band:frost", "doubleRuleGap") is not None
    assert theme_role_property_consumer("period-band:frost", "markHeight") is None
    assert theme_role_property_consumer("period-label:frost", "fontSize") is not None
    assert theme_role_property_consumer("period-label:frost", "backgroundTreatment") is None
    assert theme_catalog_pattern_consumer("period-band:frost", "pattern") is not None
    assert theme_catalog_pattern_consumer("period-label:frost", "pattern") is None


def test_stroke_alignment_is_admitted_only_for_contour_stroke_consumers():
    for role in ("planned", "gate", "network-node", "annotation-note-box", "as-of-label-chip",
                 "axis-band-decoration", "annotation-artwork", "annotation-kind-stamp"):
        assert theme_role_property_consumer(role, "strokeAlign") is not None
    for role in ("as-of-cone", "canvas-texture", "text", "dependency"):
        assert theme_role_property_consumer(role, "strokeAlign") is None


def test_theme_legend_shape_is_layout_owned_not_a_scene_paint_capability():
    assert theme_role_property_consumer("legend-swatch", "swatchShape") == "Layout legend swatch geometry and spacing"
    assert theme_role_property_consumer("planned", "swatchShape") is None
    assert theme_role_property_consumer("legend-swatch", "arbitraryShape") is None


@pytest.mark.parametrize("role", ["actual-ahead", "actual-on-track", "actual-behind"])
def test_actual_variance_traits_admit_only_fill_not_geometry_or_scene_roles(role):
    contract = theme_role_contract(role)
    assert contract is not None and not contract.scene_kinds
    assert theme_role_property_consumer(role, "fill") is not None
    for property_name in ("stroke", "strokeWidth", "strokeAlign", "markHeight", "markOffset",
                          "symbolHeight", "pattern", "gradientAngle", "opacity"):
        assert theme_role_property_consumer(role, property_name) is None


@pytest.mark.parametrize("member,property_name,value", [
    ("roles", "strokeWidth", "stroke-width"),
    ("colorBindings", "stroke", "text"),
])
def test_actual_variance_nonfill_declarations_fail_at_theme_admission(member, property_name, value):
    from chrona.presentation.color_scheme import ColorSchemeError, resolve_theme
    from tests.support import synthetic_review as sr

    parts = sr.bundle("technical-print")
    body = parts["theme"]["body"]
    if member == "roles":
        body[member]["actual-behind"] = {property_name: value}
    else:
        body[member][f"actual-behind.{property_name}"] = value
    with pytest.raises(ColorSchemeError) as failure:
        resolve_theme(parts["theme"], parts["scheme"], scheme_content_identity="sha256:" + "a" * 64)
    assert failure.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
