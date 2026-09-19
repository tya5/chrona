"""v0.2 geometry derived solely from resolved presentation settings."""
from __future__ import annotations

from dataclasses import dataclass

from .presentation_settings import PresentationSettingsError


@dataclass(frozen=True)
class PresentationRect:
    x: float
    y: float
    width: float
    height: float


def solve_presentation_layout(settings: dict) -> dict[str, PresentationRect]:
    context, layout = settings["context"], settings["layout"]
    viewport, margins = context["viewport"], layout["margins"]
    width = viewport["width"] - margins["left"] - margins["right"]
    height = viewport["height"] - margins["top"] - margins["bottom"]
    if width <= 0 or height <= 0:
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    regions = layout["regions"]
    fixed = sum(region["block"]["value"] for region in regions if region["block"]["kind"] == "fixed")
    fractional = [region for region in regions if region["block"]["kind"] == "fraction"]
    remaining = height - fixed - layout["regionGap"] * max(0, len(regions) - 1)
    if remaining < 0:
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    fraction_sum = sum(region["block"]["value"] for region in fractional) or 1
    region_rects: dict[str, PresentationRect] = {}
    y = margins["top"]
    for region in regions:
        block = region["block"]
        h = block["value"] if block["kind"] == "fixed" else remaining * block["value"] / fraction_sum
        if h < block["min"] or h > block["max"]:
            raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
        region_rects[region["id"]] = PresentationRect(margins["left"], y, width, h)
        y += h + layout["regionGap"]
    slots: dict[str, PresentationRect] = {}
    for slot_id, slot in layout["slots"].items():
        region = next((item for item in regions if item["id"] == slot["region"]), None)
        if region is None or not 0 <= slot["track"] < len(region["tracks"]):
            raise PresentationSettingsError("E_PRESENTATION_REFERENCE")
        box = region_rects[region["id"]]
        tracks = region["tracks"]
        weights = sum(track["value"] for track in tracks)
        x = box.x
        for index, track in enumerate(tracks):
            w = box.width * track["value"] / weights
            if index == slot["track"]:
                slots[slot_id] = PresentationRect(x, box.y, w, box.height)
                break
            x += w + region["gap"]
    return slots
