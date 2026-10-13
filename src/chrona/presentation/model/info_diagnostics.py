"""Typed non-fatal presentation facts shared across Layout, Scene and CLI."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
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
    budget: int
    expansions: int

    def __post_init__(self) -> None:
        if (any(not isinstance(value, str) or not value for value in (
                self.surface_id, self.relation_id, self.pass_name))
                or any(isinstance(value, bool) or not isinstance(value, int) or value < 1
                       for value in (self.budget, self.expansions))
                or self.expansions != self.budget):
            raise _diagnostic_error("RelationSearchBudgetHit requires instance/pass identity and exact exhausted count")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_SEARCH_BUDGET"

    def payload(self) -> dict[str, object]:
        return {"surfaceId": self.surface_id, "relationId": self.relation_id,
                "pass": self.pass_name,
                "budget": self.budget, "expansions": self.expansions}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


class RelationResolutionStage(str, Enum):
    NORMAL = "normal"
    LABEL_VISUALS = "label-visuals"
    TEXT = "text"
    MARKS = "marks"
    OVERLAP = "overlap"
    STUB = "stub"


@dataclass(frozen=True)
class RelationResolutionInfo:
    """One completed instance's recovery, never a discarded search-trial fact."""

    surface_id: str
    relation_id: str
    stage: RelationResolutionStage
    critical: bool

    def __post_init__(self) -> None:
        if (any(not isinstance(value, str) or not value for value in (self.surface_id, self.relation_id))
                or not isinstance(self.critical, bool)
                or not isinstance(self.stage, RelationResolutionStage)
                or self.stage is RelationResolutionStage.NORMAL):
            raise _diagnostic_error("relation resolution requires an instance and non-normal typed stage")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_RESOLUTION"

    def payload(self) -> dict[str, object]:
        return {"surfaceId": self.surface_id, "relationId": self.relation_id,
                "stage": self.stage.value, "critical": self.critical}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RelationResolutionSummary:
    """Final recovery counts, disjoint by resolved instance rather than fragment."""

    surface_id: str
    stage_counts: tuple[tuple[RelationResolutionStage, int], ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.surface_id, str) or not self.surface_id or not self.stage_counts
                or len({stage for stage, _ in self.stage_counts}) != len(self.stage_counts)
                or any(not isinstance(stage, RelationResolutionStage)
                       or stage is RelationResolutionStage.NORMAL
                       or isinstance(count, bool) or not isinstance(count, int) or count < 1
                       for stage, count in self.stage_counts)):
            raise _diagnostic_error("relation resolution summary requires unique positive stage counts")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_RESOLUTION_SUMMARY"

    def payload(self) -> dict[str, object]:
        return {"surfaceId": self.surface_id, "count": sum(count for _, count in self.stage_counts),
                "stages": {stage.value: count for stage, count in self.stage_counts}}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RelationPolicySupersession:
    """A declared View overflow is superseded only for spatial Layout routing."""

    surface_id: str
    view_overflow: str
    layout_mode: str

    def __post_init__(self) -> None:
        if (not isinstance(self.surface_id, str) or not self.surface_id
                or self.view_overflow not in {"suppress", "visible-overflow"}
                or self.layout_mode not in {"relax", "overlap", "stub", "suppress"}
                or (self.view_overflow == self.layout_mode == "suppress")):
            raise _diagnostic_error("relation policy supersession requires a changed declared spatial policy")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_POLICY_SUPERSEDED"

    def payload(self) -> dict[str, object]:
        return {"surfaceId": self.surface_id, "viewMember": "visibility.relations.overflow",
                "viewValue": self.view_overflow, "layoutMember": "relationRouting.unroutable",
                "layoutValue": self.layout_mode}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RelationHintReceipt:
    surface_id: str
    relation_id: str
    disposition: str
    reason: str
    searched: bool

    def __post_init__(self) -> None:
        if (any(not isinstance(value, str) or not value for value in (self.surface_id, self.relation_id, self.reason))
                or self.disposition not in {"accepted", "invalidated", "unusable", "absent"}
                or not isinstance(self.searched, bool) or (self.disposition == "accepted" and self.searched)):
            raise _diagnostic_error("hint receipt requires one admitted instance, disposition and honest search count")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_HINT"

    def payload(self) -> dict[str, object]:
        return {"surfaceId": self.surface_id, "relationId": self.relation_id,
                "disposition": self.disposition, "reason": self.reason, "searched": self.searched}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RelationHintSummary:
    surface_id: str
    receipts: tuple[RelationHintReceipt, ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.surface_id, str) or not self.surface_id
                or any(item.surface_id != self.surface_id for item in self.receipts)
                or len({item.relation_id for item in self.receipts}) != len(self.receipts)):
            raise _diagnostic_error("hint summary requires unique instances on one surface")

    @property
    def code(self) -> str:
        return "I_LAYOUT_RELATION_HINT_SUMMARY"

    def payload(self) -> dict[str, object]:
        counts = {name: sum(item.disposition == name for item in self.receipts)
                  for name in ("accepted", "invalidated", "unusable", "absent")}
        return {"surfaceId": self.surface_id, "relationInstances": len(self.receipts), **counts,
                "ordinarySelection": len(self.receipts) - counts["accepted"],
                "actualSearch": sum(item.searched for item in self.receipts)}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


PresentationInfo = (SuppressedPlotLabels | PaintOmission | RelationRoutingSummary | RelationSearchBudgetHit
                    | RelationResolutionInfo | RelationResolutionSummary | RelationPolicySupersession
                    | RelationHintReceipt | RelationHintSummary)
