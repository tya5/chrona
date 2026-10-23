"""Layout receives the same selected-profile ink admission as Scene."""
import pytest

from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.scene.visual_capabilities import (
    BASELINE_PROFILE, PDF_PROFILE, PNG_ICON_PROFILE, SVG_ICON_PROFILE,
    paint_witness_capabilities, resolve_visual_profile,
)


@pytest.mark.parametrize("identifier,target,gradient,optional,line_finish", [
    (BASELINE_PROFILE, "svg", False, True, False),
    (SVG_ICON_PROFILE, "svg", True, False, True),
    (PNG_ICON_PROFILE, "png", True, False, True),
    (PDF_PROFILE, "pdf", False, True, True),
])
def test_selected_profile_closes_neutral_ink_capabilities(identifier, target, gradient, optional, line_finish):
    result = paint_witness_capabilities(resolve_visual_profile(identifier, target))
    assert result == PaintWitnessCapabilities(
        gradient_supported=gradient, optional_gradient_omission=optional,
        line_finish_supported=line_finish, optional_line_finish_omission=optional)


def test_unrestricted_internal_profile_keeps_existing_gradient_admission():
    assert paint_witness_capabilities(None) == PaintWitnessCapabilities(
        gradient_supported=True, optional_gradient_omission=False,
        line_finish_supported=True, optional_line_finish_omission=False)
