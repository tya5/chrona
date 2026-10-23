"""Neutral profile admission shared by Layout ink witnesses and Scene paint."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PaintWitnessCapabilities:
    gradient_supported: bool = True
    optional_gradient_omission: bool = False
    line_finish_supported: bool = True
    optional_line_finish_omission: bool = False
