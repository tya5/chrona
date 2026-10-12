"""Typed non-fatal presentation facts shared across Layout, Scene and CLI."""
from __future__ import annotations

from dataclasses import dataclass
import json


def _shown(value: object) -> str:
    text = repr(value)
    return text if len(text) <= 96 else text[:93] + "..."


def _diagnostic_error(detail: str) -> ValueError:
    return ValueError(f"E_PRESENTATION_INFO_INVALID: {detail}")


@dataclass(frozen=True)
class SuppressedPlotLabels:
    """One completed surface's declared plot-label suppression count."""

    surface_id: str
    count: int

    def __post_init__(self) -> None:
        if not self.surface_id or any(char in self.surface_id for char in ";=") or self.count <= 0:
            raise _diagnostic_error(f"SuppressedPlotLabels surfaceId={_shown(self.surface_id)}, count={_shown(self.count)}; expected nonempty delimiter-safe id and positive count")

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
                or self.treatment not in {"linear-gradient", "drop-shadow", "glow", "wobble", "stroke-finish", "as-of-cone",
                                       "annotation-artwork", "frame-glyph", "canvas-texture", "canvas-overlay",
                                       "canvas-overlay-gradient"}
                or not self.source_ref.startswith("/body/roles/")
                or not self.visual_profile or any(char in self.visual_profile for char in ";=")
                or not self.target_kind
                or (self.paintable_profile is not None
                    and (not self.paintable_profile or any(char in self.paintable_profile for char in ";=")))):
            invalid = tuple(name for name, value in (
                ("role", self.role), ("treatment", self.treatment), ("sourceRef", self.source_ref),
                ("visualProfile", self.visual_profile), ("targetKind", self.target_kind),
                ("paintableProfile", self.paintable_profile))
                if (not value or (name in {"role", "visualProfile", "paintableProfile"} and value is not None and any(char in value for char in ";="))
                    or (name == "treatment" and value not in {"linear-gradient", "drop-shadow", "glow", "wobble", "stroke-finish", "as-of-cone", "annotation-artwork", "frame-glyph", "canvas-texture", "canvas-overlay", "canvas-overlay-gradient"})
                    or (name == "sourceRef" and not value.startswith("/"))))
            raise _diagnostic_error(f"PaintOmission invalid fields={invalid!r}; treatment={_shown(self.treatment)}, sourceRef={_shown(self.source_ref)}, targetKind={_shown(self.target_kind)}")

    @property
    def code(self) -> str:
        return "I_VISUAL_TREATMENT_OMITTED"

    def scene_diagnostic(self) -> str:
        suggested = self.paintable_profile or "none"
        return (f"{self.code}:role={self.role};treatment={self.treatment};"
                f"profile={self.visual_profile};paintable={suggested}")


@dataclass(frozen=True)
class RelationRoutingSummary:
    """Disjoint completed first-fit counts from the Layout selection producer."""

    surface_id: str
    relation_instances: int
    shape_settled: int
    fallback_search: int

    def __post_init__(self) -> None:
        counts = (self.relation_instances, self.shape_settled, self.fallback_search)
        if (not isinstance(self.surface_id, str) or not self.surface_id
                or any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts)
                or self.shape_settled + self.fallback_search > self.relation_instances):
            raise _diagnostic_error("RelationRoutingSummary requires a surface id and disjoint nonnegative integer counts")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_ROUTING"

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps({"surfaceId": self.surface_id,
            "relationInstances": self.relation_instances, "shapeSettled": self.shape_settled,
            "fallbackSearch": self.fallback_search}, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RelationSearchBudgetHit:
    """A completed Layout instance/pass exhausted its declared additional ceiling."""

    surface_id: str
    relation_id: str
    pass_name: str
    search: str
    budget: int
    expansions: int

    def __post_init__(self) -> None:
        if (any(not isinstance(value, str) or not value for value in (
                self.surface_id, self.relation_id, self.pass_name))
                or self.search not in {"first-fit", "best"}
                or any(isinstance(value, bool) or not isinstance(value, int) or value < 1
                       for value in (self.budget, self.expansions))
                or self.expansions != self.budget):
            raise _diagnostic_error("RelationSearchBudgetHit requires instance/pass identity and exact exhausted count")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_SEARCH_BUDGET"

    def payload(self) -> dict[str, object]:
        return {"surfaceId": self.surface_id, "relationId": self.relation_id,
                "pass": self.pass_name, "search": self.search,
                "budget": self.budget, "expansions": self.expansions}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


PresentationInfo = SuppressedPlotLabels | PaintOmission | RelationRoutingSummary | RelationSearchBudgetHit
