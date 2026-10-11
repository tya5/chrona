"""Natural axis-bucket fit uses the same painted bounds as completed text."""
from copy import deepcopy
from dataclasses import replace

import pytest

from chrona.presentation.layout.surface_axis import _axis_text_run_geometry, measure_axis_tier
from chrona.presentation.layout.surface_base import prepare_surface_base
from chrona.presentation.model.surface_content import AxisLabelIntent, AxisTier
from chrona.presentation.model.theme_tokens import ThemeTokenView
from tests.unit.chrona.presentation.layout.test_surface_axis_tier_geometry import _axis_request
from tests.unit.chrona.presentation.scene import test_v05_builder as fixtures


class _AsymmetricNumericFont:
    content_identity = "sha256:axis-natural-typography"

    def width(self, content, size, *, letter_spacing=0, numeric_spacing="proportional"):
        advances = []
        for character in content:
            if character.isdigit():
                advances.append(7.0 if numeric_spacing == "tabular" else 3.0 + int(character) / 10)
            elif character in "MW":
                advances.append(12.0)
            else:
                advances.append(5.0)
        return sum(advances) * size / 10 + max(0, len(content) - 1) * letter_spacing


@pytest.mark.parametrize(
    "orientation,form,transform,numeric_spacing,horizontal_scale",
    [
        ("horizontal", "short-month", "uppercase", "proportional", 0.5),
        ("rotate-cw", "short-month", "capitalize", "proportional", 0.75),
        ("rotate-ccw", "numeric-month", "none", "tabular", 1.0),
        ("horizontal", "numeric-month", "none", "proportional", 1.0),
    ],
)
def test_natural_bucket_fit_matches_completed_text_bounds_at_threshold(
    orientation, form, transform, numeric_spacing, horizontal_scale,
):
    tier = AxisTier("month", 1, "labels", AxisLabelIntent(
        form, (), "start", "thin-with-record", orientation, "en-US"))
    request = _axis_request((tier,))
    theme = deepcopy(fixtures._theme())
    theme["body"]["values"].update({
        "axis-letter-spacing": {"type": "number", "value": "0.75"},
        "axis-text-transform": {"type": "textTransform", "value": transform},
        "axis-numeric-spacing": {"type": "numericSpacing", "value": numeric_spacing},
        "axis-horizontal-scale": {"type": "number", "value": horizontal_scale},
        "axis-label-inset": {"type": "number", "value": "0.2"},
    })
    theme["body"]["roles"]["axis"].update({
        "letterSpacing": "axis-letter-spacing",
        "textTransform": "axis-text-transform",
        "numericSpacing": "axis-numeric-spacing",
        "horizontalScale": "axis-horizontal-scale",
        "labelInset": "axis-label-inset",
    })
    request = replace(request, theme_tokens=ThemeTokenView(theme), font_metrics=_AsymmetricNumericFont())
    base_scale = prepare_surface_base(request).scale

    # Measure once to obtain the natural bucket label and exact completed text extent.
    initial = measure_axis_tier(request, base_scale, 0, tier)
    natural = initial.intervals[0]
    outcome = initial.outcomes[0]
    run = _axis_text_run_geometry(
        content=outcome.label,
        inline=0,
        baseline_block=0,
        treatment=initial.treatment,
        metrics=initial.metrics,
        orientation=orientation,
    )
    inset = float(initial.treatment.font_size) * 0.2
    required_inline = float(run.bounds.inline_size) + inset
    duration_days = (natural.natural_end - natural.natural_start).days

    # Put the bucket just below and just above its exact natural fit boundary.
    for delta, expected_fit in ((-0.001, False), (0.001, True)):
        scale = replace(base_scale, unit_ratio=(required_inline + delta) / duration_days)
        measured = measure_axis_tier(request, scale, 0, tier)
        candidate = measured.outcomes[0]
        actual_available = duration_days * scale.unit_ratio - inset
        completed = _axis_text_run_geometry(
            content=candidate.label,
            inline=0,
            baseline_block=0,
            treatment=measured.treatment,
            metrics=measured.metrics,
            orientation=orientation,
        )
        expected_from_completed_bounds = float(completed.bounds.inline_size) <= actual_available
        assert expected_from_completed_bounds is expected_fit
        assert candidate.label_fits is expected_from_completed_bounds
        assert candidate.start == natural.start and candidate.end == natural.end
        assert (candidate.natural_start, candidate.natural_end) == (
            natural.natural_start, natural.natural_end)
