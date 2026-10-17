"""Typed non-fatal presentation facts shared across Layout, Scene and CLI."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import ClassVar

from chrona.core.diagnostics import Diagnostic


def _shown(value: object) -> str:
    text = repr(value)
    return text if len(text) <= 96 else text[:93] + "..."


def _diagnostic_error(detail: str) -> ValueError:
    return ValueError(f"E_PRESENTATION_INFO_INVALID: {detail}")


@dataclass(frozen=True)
class ForecastInfo:
    """One published informational finding produced by the forecast analysis."""

    diagnostic: Diagnostic

    _ALLOWED_CODES: ClassVar[frozenset[str]] = frozenset({
        "I_FORECAST_MOVED",
        "I_FORECAST_START_UNOBSERVED",
        "I_FORECAST_ROLLUP_OBSERVATION_CONFLICT",
        "E_FIXED_TARGET_VIOLATION",
    })

    def __post_init__(self) -> None:
        if (not isinstance(self.diagnostic, Diagnostic)
                or self.diagnostic.id not in self._ALLOWED_CODES):
            identifier = getattr(self.diagnostic, "id", None)
            raise _diagnostic_error(
                f"ForecastInfo diagnosticId={_shown(identifier)}; expected one of "
                f"{tuple(sorted(self._ALLOWED_CODES))!r}")

    @property
    def code(self) -> str:
        return self.diagnostic.id

    def payload(self) -> dict[str, object]:
        result: dict[str, object] = {"message": self.diagnostic.message}
        if self.diagnostic.path is not None:
            result["path"] = self.diagnostic.path
        if self.diagnostic.details is not None:
            result["details"] = dict(self.diagnostic.details)
        return result

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(
            self.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
class DeadlineCaptionsDropped:
    """Optional caption occurrences that did not fit either approved anchor."""

    surface_id: str
    count: int

    def __post_init__(self) -> None:
        if (not self.surface_id or any(char in self.surface_id for char in ";=")
                or isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 1):
            raise _diagnostic_error("DeadlineCaptionsDropped requires a surface id and positive occurrence count")

    @property
    def code(self) -> str:
        return "I_LAYOUT_DEADLINE_CAPTION_DROPPED"

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


@dataclass(frozen=True)
class UnboundSummarySource:
    """An optional Summary connection omitted before content measurement."""

    panel_id: str
    metric_id: str
    source_kind: str
    source_name: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if (self.source_kind not in {"slot", "figure"}
                or any(not isinstance(value, str) or not value
                       for value in (self.panel_id, self.metric_id, self.source_name))):
            raise _diagnostic_error("UnboundSummarySource requires consumer ids and a slot or figure name")

    @property
    def code(self) -> str:
        if self.reason is not None:
            return "W_SUMMARY_SLOT_UNAVAILABLE"
        return "W_SUMMARY_SLOT_UNBOUND" if self.source_kind == "slot" else "I_SUMMARY_FIGURE_UNBOUND"

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps({"panel": self.panel_id,
            "metric": self.metric_id, self.source_kind: self.source_name,
            **({"reason": self.reason} if self.reason is not None else {})},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class UnboundFieldRole:
    """Count role-bound View declarations unavailable on the primary Project."""

    role: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not self.role or not self.source_refs or len(set(self.source_refs)) != len(self.source_refs)
                or any(not path.startswith("/body/") for path in self.source_refs)):
            raise _diagnostic_error("UnboundFieldRole requires a role and distinct View declaration paths")

    @property
    def code(self) -> str:
        return "I_VIEW_FIELD_ROLE_UNBOUND"

    @property
    def count(self) -> int:
        return len(self.source_refs)

    def payload(self) -> dict[str, object]:
        return {"fieldRole": self.role, "count": self.count, "sourceRefs": list(self.source_refs)}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class FontGlyphFallback:
    """An automatically covered glyph with its exact measured face."""

    requested_family: str
    fallback_family: str
    weight: int
    codepoint: int
    text: str

    @property
    def code(self) -> str:
        return "I_FONT_GLYPH_SUBSTITUTED"

    def payload(self) -> dict[str, object]:
        return {"requestedFamily": self.requested_family, "fallbackFamily": self.fallback_family,
                "weight": self.weight, "codepoint": f"U+{self.codepoint:04X}", "text": self.text}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class ScaleValuesFolded:
    """Categorical values beyond a colour scale's distinct hues, drawn as one neutral "Other" (#1628)."""

    scale_id: str
    source_field: str
    palette_size: int
    values: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not self.scale_id or not self.source_field or not self.values
                or isinstance(self.palette_size, bool) or not isinstance(self.palette_size, int) or self.palette_size < 1):
            raise _diagnostic_error("ScaleValuesFolded requires a scale, a field, a positive palette size and folded values")

    @property
    def code(self) -> str:
        return "I_PRESENTATION_SCALE_FOLDED"

    def payload(self) -> dict[str, object]:
        return {"scaleId": self.scale_id, "field": self.source_field, "distinctColors": self.palette_size,
                "foldedCount": len(self.values), "folded": list(self.values)}

    def scene_diagnostic(self) -> str:
        return self.code + ":" + json.dumps(self.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


PresentationInfo = (ScaleValuesFolded | FontGlyphFallback | SuppressedPlotLabels | DeadlineCaptionsDropped | PaintOmission | ForecastInfo | RelationRoutingSummary | RelationSearchBudgetHit
                    | RelationResolutionInfo | RelationResolutionSummary | RelationPolicySupersession
                    | RelationHintReceipt | RelationHintSummary | UnboundSummarySource | UnboundFieldRole)
