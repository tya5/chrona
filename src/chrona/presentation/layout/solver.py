"""M19 declarative layout-profile validation and deterministic manifest."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from typing import Any
import jsonschema
import yaml


SOURCES = {"title", "table", "timeline", "summary", "legend", "annotations", "notes"}


@dataclass(frozen=True)
class LayoutManifest:
    profile_id: str
    content_hash: str
    regions: tuple[tuple[str, str], ...]
    slots: tuple[tuple[str, str, str], ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class Rect:
    x: int; y: int; width: int; height: int


def resolve_layout_profile(profile: dict[str, Any], available_sources: set[str]) -> LayoutManifest:
    """Validate only declarative composition; never inspect Project or renderer state."""
    if profile.get("version") != "chrona/layout-profile/v0.1":
        raise ValueError("E_LAYOUT_PROFILE_REQUIRED")
    required={"version","id","canvas","regions","slots","constraints"}
    if not required <= set(profile) or set(profile)-required-{"surface"}: raise ValueError("E_LAYOUT_PROFILE_SHAPE")
    schema_path = files("chrona.resources").joinpath("schemas", "layout-profile-v0.1.schema.yaml")
    if list(jsonschema.Draft202012Validator(yaml.safe_load(schema_path.read_text())).iter_errors(profile)):
        raise ValueError("E_LAYOUT_PROFILE_SCHEMA")
    canvas=profile["canvas"]
    if set(canvas) != {"aspectRatio","margin","density"} or canvas["aspectRatio"] not in {"16:9","4:3","free"} or canvas["margin"] not in {"compact","balanced","spacious"}: raise ValueError("E_LAYOUT_CANVAS")
    region_ids=[r.get("id") for r in profile["regions"]]
    if any(not isinstance(x,str) or not x for x in region_ids) or len(region_ids)!=len(set(region_ids)): raise ValueError("E_LAYOUT_REGION_ID")
    regions=tuple((r["id"],r["layout"]) for r in profile["regions"])
    diagnostics=[]; slots=[]
    for slot_id,slot in profile["slots"].items():
        if set(slot) != {"region","source","priority","overflow","role"}: diagnostics.append(f"E_LAYOUT_SLOT_SHAPE:{slot_id}")
        if slot.get("region") not in region_ids: diagnostics.append(f"E_LAYOUT_REGION_UNKNOWN:{slot_id}")
        if slot.get("source") not in SOURCES: diagnostics.append(f"E_LAYOUT_SOURCE_UNKNOWN:{slot_id}")
        if slot.get("source") not in available_sources and slot.get("priority")=="required": diagnostics.append(f"E_LAYOUT_SOURCE_UNAVAILABLE:{slot_id}")
        slots.append((slot_id,slot.get("region",""),slot.get("source","")))
    if profile["constraints"].get("overlap") != "diagnose": diagnostics.append("E_LAYOUT_OVERLAP_POLICY")
    raw=repr(profile).encode(); return LayoutManifest(str(profile["id"]),sha256(raw).hexdigest(),regions,tuple(sorted(slots)),tuple(sorted(diagnostics)))


def solve_layout(profile: dict[str, Any], manifest: LayoutManifest) -> dict[str, Rect]:
    """Resolve a small closed grid vocabulary into derived slot rectangles."""
    if manifest.diagnostics: raise ValueError("E_LAYOUT_DIAGNOSTICS")
    width,height={("16:9"):(1600,900),"4:3":(1200,900),"free":(1400,900)}[profile["canvas"]["aspectRatio"]]
    margin={"compact":24,"balanced":48,"spacious":72}[profile["canvas"]["margin"]]
    regions=profile["regions"]; usable_h=height-margin*2; header_h=96 if any(r["id"]=="header" for r in regions) else 0; footer_h=120 if any(r["id"]=="footer" for r in regions) else 0
    rects: dict[str,Rect]={}; y=margin
    for region in regions:
        rid=region["id"]
        h=header_h if rid=="header" else footer_h if rid=="footer" else usable_h-header_h-footer_h
        rects[rid]=Rect(margin,y,width-margin*2,h); y+=h
        if region["layout"]=="split":
            tracks=region.get("tracks",["1fr","1fr"]); weights=[int(x[:-2]) if x.endswith("fr") else int(x[:-1]) for x in tracks]; total=sum(weights); x=margin
            for i,w in enumerate(weights):
                part=(width-margin*2)*w//total; rects[f"{rid}.{i}"]=Rect(x,rects[rid].y,part,rects[rid].height); x+=part
    slots={}
    split_indices: dict[str,int]={}
    for sid,slot in profile["slots"].items():
        base=slot["region"]; index=split_indices.get(base,0); candidate=f"{base}.{index}"
        slots[sid]=rects.get(candidate,rects[base]); split_indices[base]=index+1
    return slots


def validate_designer_preset(resources: dict[str, dict[str, Any]], available_sources: set[str]) -> dict[str, Any]:
    """Common human/AI declarative preset gateway; executable payloads are rejected."""
    required={"view","style","theme","layout"}
    if set(resources) != required: raise ValueError("E_PRESET_CLOSURE")
    if any("code" in value or "svg" in value for value in resources.values()): raise ValueError("E_PRESET_EXECUTABLE_CONTENT")
    manifest=resolve_layout_profile(resources["layout"],available_sources)
    if manifest.diagnostics: raise ValueError(",".join(manifest.diagnostics))
    hashes={name:sha256(repr(value).encode()).hexdigest() for name,value in sorted(resources.items())}
    return {"layoutManifest":manifest,"resourceHashes":hashes}
