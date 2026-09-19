"""M19 declarative layout-profile validation and deterministic manifest."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any


SOURCES = {"title", "table", "timeline", "summary", "legend", "annotations", "notes"}


@dataclass(frozen=True)
class LayoutManifest:
    profile_id: str
    content_hash: str
    regions: tuple[tuple[str, str], ...]
    slots: tuple[tuple[str, str, str], ...]
    diagnostics: tuple[str, ...]


def resolve_layout_profile(profile: dict[str, Any], available_sources: set[str]) -> LayoutManifest:
    """Validate only declarative composition; never inspect Project or renderer state."""
    if profile.get("version") != "chrona/layout-profile/v0.1":
        raise ValueError("E_LAYOUT_PROFILE_REQUIRED")
    required={"version","id","canvas","regions","slots","constraints"}
    if set(profile) != required: raise ValueError("E_LAYOUT_PROFILE_SHAPE")
    region_ids=[r.get("id") for r in profile["regions"]]
    if any(not isinstance(x,str) or not x for x in region_ids) or len(region_ids)!=len(set(region_ids)): raise ValueError("E_LAYOUT_REGION_ID")
    regions=tuple((r["id"],r["layout"]) for r in profile["regions"])
    diagnostics=[]; slots=[]
    for slot_id,slot in profile["slots"].items():
        if slot.get("region") not in region_ids: diagnostics.append(f"E_LAYOUT_REGION_UNKNOWN:{slot_id}")
        if slot.get("source") not in SOURCES: diagnostics.append(f"E_LAYOUT_SOURCE_UNKNOWN:{slot_id}")
        if slot.get("source") not in available_sources and slot.get("priority")=="required": diagnostics.append(f"E_LAYOUT_SOURCE_UNAVAILABLE:{slot_id}")
        slots.append((slot_id,slot.get("region",""),slot.get("source","")))
    if profile["constraints"].get("overlap") != "diagnose": diagnostics.append("E_LAYOUT_OVERLAP_POLICY")
    raw=repr(profile).encode(); return LayoutManifest(str(profile["id"]),sha256(raw).hexdigest(),regions,tuple(sorted(slots)),tuple(sorted(diagnostics)))
