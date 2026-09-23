import pytest

from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale


def _scale():
    return resolve_color_scale(
        {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus", "payload"]},
        {"owner": {"slots": {"bus": "bus", "payload": "payload"}}},
        {"bus": "#112233", "payload": "#445566"},
    )


def test_scale_resolves_explicit_value_to_named_slot():
    assert _scale().color_for("bus-task", {"owner": "bus"}) == "#112233"


def test_scale_rejects_unknown_or_missing_selected_value():
    with pytest.raises(ColorScaleError, match="E_PRESENTATION_SCALE_VALUE:task:owner"):
        _scale().color_for("task", {"owner": "other"})
    with pytest.raises(ColorScaleError, match="E_PRESENTATION_SCALE_VALUE:task:owner"):
        _scale().color_for("task", {})


def test_scale_requires_an_exact_mapping_and_existing_slot():
    with pytest.raises(ColorScaleError, match="E_PRESENTATION_SCALE_MAPPING"):
        resolve_color_scale(
            {"scale": "owner", "target": "planned", "source": {"field": "owner"}, "domain": ["bus"]},
            {"owner": {"slots": {"payload": "payload"}}}, {"payload": "#445566"},
        )
