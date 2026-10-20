"""Typed, countable Layout evidence for a requested route style fallback."""
from dataclasses import dataclass
import json
from typing import Literal


@dataclass(frozen=True)
class RelationStyleFallback:
    relation_id: str
    reason: Literal["clearance", "bounds", "self-overlap", "terminal", "recovery"]
    requested: Literal["curved", "metro"] = "curved"
    actual: Literal["orthogonal"] = "orthogonal"

    def __post_init__(self) -> None:
        if (not self.relation_id or self.reason not in {
                "clearance", "bounds", "self-overlap", "terminal", "recovery"}
                or self.requested not in {"curved", "metro"} or self.actual != "orthogonal"):
            raise ValueError("E_LAYOUT_PATH_INPUT: invalid relation style fallback")

    @property
    def diagnostic(self) -> str:
        return "I_LAYOUT_RELATION_STYLE_FALLBACK:" + json.dumps({
            "relationId": self.relation_id, "requested": self.requested,
            "actual": self.actual, "reason": self.reason,
        }, sort_keys=True, separators=(",", ":"))
