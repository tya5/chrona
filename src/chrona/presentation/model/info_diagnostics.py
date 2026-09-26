"""Typed non-fatal presentation facts shared across Layout, Scene and CLI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuppressedPlotLabels:
    """One completed surface's declared plot-label suppression count."""

    surface_id: str
    count: int

    def __post_init__(self) -> None:
        if not self.surface_id or any(char in self.surface_id for char in ";=") or self.count <= 0:
            raise ValueError("E_PRESENTATION_INFO_INVALID")

    @property
    def code(self) -> str:
        return "I_LAYOUT_PLOT_LABELS_SUPPRESSED"

    def scene_diagnostic(self) -> str:
        return f"{self.code}:surface={self.surface_id};count={self.count}"


@dataclass(frozen=True)
class PaintOmission:
    """One optional Theme treatment omitted by a selected target profile."""

    role: str
    treatment: str
    source_ref: str
    visual_profile: str
    target_kind: str
    paintable_profile: str | None

    def __post_init__(self) -> None:
        if (not self.role or any(char in self.role for char in ";=")
                or self.treatment not in {"linear-gradient", "drop-shadow", "stroke-finish"}
                or not self.source_ref.startswith("/body/roles/")
                or not self.visual_profile or any(char in self.visual_profile for char in ";=")
                or not self.target_kind
                or (self.paintable_profile is not None
                    and (not self.paintable_profile or any(char in self.paintable_profile for char in ";=")))):
            raise ValueError("E_PRESENTATION_INFO_INVALID")

    @property
    def code(self) -> str:
        return "I_VISUAL_TREATMENT_OMITTED"

    def scene_diagnostic(self) -> str:
        suggested = self.paintable_profile or "none"
        return (f"{self.code}:role={self.role};treatment={self.treatment};"
                f"profile={self.visual_profile};paintable={suggested}")


PresentationInfo = SuppressedPlotLabels | PaintOmission
