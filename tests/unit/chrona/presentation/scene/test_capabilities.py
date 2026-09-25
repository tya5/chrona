import pytest

from chrona.presentation.scene.capabilities import (
    CapabilityDisposition,
    LINEAR_GRADIENT,
    admitted_capability_ids,
    capability_ceiling,
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
