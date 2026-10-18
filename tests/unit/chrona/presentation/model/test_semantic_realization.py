from chrona.presentation.model.semantic_realization import purpose_classifications


def test_summary_bar_purpose_is_registered_as_unpainted_until_a_consumer_is_selected():
    classifications = {item.purpose: item for item in purpose_classifications()}

    assert classifications["summary-bar"].disposition == "unpainted"
    assert "overlay-only role is not activated" in classifications["summary-bar"].reason
