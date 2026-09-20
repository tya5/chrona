"""v0.2 geometry derived solely from resolved presentation settings."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping

from chrona.presentation.presentation_settings import PresentationSettingsError


@dataclass(frozen=True)
class PresentationRect:
    x: float
    y: float
    width: float
    height: float


def _measure(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value < 0:
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    return float(value)


def _sizes(tracks: list[dict], available: float, gap: float, intrinsic: Mapping[int, float]) -> list[float]:
    if any(track["min"] > track["max"] for track in tracks):
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    remaining = available - gap * max(0, len(tracks) - 1)
    sizes: list[float | None] = [None] * len(tracks)
    fractions: list[tuple[int, float]] = []
    for index, track in enumerate(tracks):
        kind = track["kind"]
        if kind == "fixed":
            size = _measure(track.get("value"))
        elif kind == "content":
            if "value" in track or index not in intrinsic:
                raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
            size = _measure(intrinsic[index])
        elif kind == "fraction":
            fractions.append((index, _measure(track.get("value"))))
            continue
        else:
            raise PresentationSettingsError("E_PRESENTATION_REFERENCE")
        sizes[index] = size
        remaining -= size
    if remaining < 0:
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    if fractions:
        total = sum(weight for _, weight in fractions)
        if total <= 0:
            raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
        for index, weight in fractions:
            sizes[index] = remaining * weight / total
    elif remaining > 0:
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    completed = [float(size) for size in sizes]
    if any(size < track["min"] or size > track["max"] for size, track in zip(completed, tracks)):
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    return completed


def solve_presentation_layout(settings: dict, *, intrinsic_blocks: Mapping[str, float] | None = None, intrinsic_tracks: Mapping[str, Mapping[int, float]] | None = None) -> dict[str, PresentationRect]:
    """Resolve fixed/content first, then fraction tracks; never invent an intrinsic size."""
    context, layout = settings["context"], settings["layout"]
    viewport, margins = context["viewport"], layout["margins"]
    width = viewport["width"] - margins["left"] - margins["right"]
    height = viewport["height"] - margins["top"] - margins["bottom"]
    if width <= 0 or height <= 0:
        raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
    regions = layout["regions"]
    intrinsic_blocks, intrinsic_tracks = intrinsic_blocks or {}, intrinsic_tracks or {}
    blocks: list[dict] = []
    block_inputs: dict[int, float] = {}
    for index, region in enumerate(regions):
        block = dict(region["block"])
        blocks.append(block)
        if block["kind"] == "content":
            if region["id"] not in intrinsic_blocks:
                raise PresentationSettingsError("E_LAYOUT_REQUIRED_OVERFLOW")
            block_inputs[index] = intrinsic_blocks[region["id"]]
    heights = _sizes(blocks, height, layout["regionGap"], block_inputs)
    region_rects: dict[str, PresentationRect] = {}
    y = margins["top"]
    for region, h in zip(regions, heights):
        region_rects[region["id"]] = PresentationRect(margins["left"], y, width, h)
        y += h + layout["regionGap"]
    slots: dict[str, PresentationRect] = {}
    for slot_id, slot in layout["slots"].items():
        region = next((item for item in regions if item["id"] == slot["region"]), None)
        if region is None or not 0 <= slot["track"] < len(region["tracks"]):
            raise PresentationSettingsError("E_PRESENTATION_REFERENCE")
        box = region_rects[region["id"]]
        widths = _sizes(region["tracks"], box.width, region["gap"], intrinsic_tracks.get(region["id"], {}))
        x = box.x
        for index, track_width in enumerate(widths):
            if index == slot["track"]:
                slots[slot_id] = PresentationRect(x, box.y, track_width, box.height)
                break
            x += track_width + region["gap"]
    return slots
