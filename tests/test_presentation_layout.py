from copy import deepcopy

import pytest

from chrona.presentation_layout import solve_presentation_layout
from chrona.presentation_settings import PresentationSettingsError, builtin_bases


def test_regions_and_slots_are_derived_from_resolved_settings():
    settings = builtin_bases()["executive-v0.2"]
    slots = solve_presentation_layout(settings)
    assert slots["table"].width / slots["timeline"].width == pytest.approx(3 / 7)
    assert slots["table"].y == slots["timeline"].y


def test_unsatisfied_minimum_is_diagnosed():
    settings = deepcopy(builtin_bases()["executive-v0.2"])
    settings["context"]["viewport"]["height"] = 100
    with pytest.raises(PresentationSettingsError, match="E_LAYOUT_REQUIRED_OVERFLOW"):
        solve_presentation_layout(settings)
