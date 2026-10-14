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
