import pytest

from chrona.presentation.scene.capabilities import (
    CapabilityDisposition,
    LINEAR_GRADIENT,
    admitted_capability_ids,
    capability_ceiling,
    theme_catalog_pattern_consumer,
    theme_role_property_consumer,
    validate_substitution_request,
)


def test_capability_ceiling_records_every_disposition_and_runtime_id_is_admitted():
    ceiling = capability_ceiling()
    assert {item.disposition for item in ceiling} == set(CapabilityDisposition)
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
