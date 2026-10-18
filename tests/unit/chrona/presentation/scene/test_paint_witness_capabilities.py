"""Layout receives the same selected-profile ink admission as Scene."""
import pytest

from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, PDF_PROFILE, PNG_ICON_PROFILE, SVG_ICON_PROFILE,
    paint_witness_capabilities, resolve_visual_profile,
)


@pytest.mark.parametrize("identifier,target,supported,optional", [
    (BASELINE_PROFILE, "svg", False, True),
    (SVG_ICON_PROFILE, "svg", True, False),
    (PNG_ICON_PROFILE, "png", True, False),
    (PDF_PROFILE, "pdf", False, True),
])
def test_selected_profile_closes_neutral_ink_capabilities(identifier, target, supported, optional):
    result = paint_witness_capabilities(resolve_visual_profile(identifier, target))
    assert result == PaintWitnessCapabilities(supported, optional)


def test_unrestricted_internal_profile_keeps_existing_gradient_admission():
    assert paint_witness_capabilities(None) == PaintWitnessCapabilities(True, False)
