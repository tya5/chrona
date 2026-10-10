"""Checks on the HALCYON board rendered through each catalogue preset (#657).

These are the assertions of what used to be four separate tests (distinct axis band,
bounded axis cells, start-aligned month labels, print-mono greyscale).  They take an
already-rendered Scene, so `tests/integration/test_halcyon_preset_renders.py` can render
each preset once and run every check on it in one test item; see the #657 design,
"Session boundary".
"""
from __future__ import annotations

import pytest

MINIMUM_BAND_CONTRAST = 1.15


def primitives(scene: dict) -> list[dict]:
    found: list[dict] = []

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and "paint" in value:
                found.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(scene)
    return found


def _rgb(colour: str) -> tuple[float, float, float]:
    colour = colour.lstrip("#")
    red, green, blue = (int(colour[index:index + 2], 16) / 255 for index in (0, 2, 4))
    return red, green, blue


def _composite(paint: dict, canvas: tuple[float, float, float]) -> tuple[float, float, float]:
    opacity = float(paint.get("opacity", 1.0))
    red, green, blue = (opacity * part + (1 - opacity) * ground for part, ground in zip(_rgb(paint["fill"]), canvas))
    return red, green, blue


def _luminance(rgb: tuple[float, float, float]) -> float:
    linear = [part / 12.92 if part <= 0.04045 else ((part + 0.055) / 1.055) ** 2.4 for part in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def band_contrasts(scene: dict) -> list[tuple[str, str, float]]:
    results = []
    for surface in scene.get("surfaces", ()):
        canvas = _rgb(surface.get("canvasPaint", {}).get("fill", "#FFFFFF"))
        found = primitives(surface)
        axis = [item for item in found if item.get("visualRole") == "axis-band-decoration" and "fill" in item["paint"]]
        bands = [item for item in found
                 if item.get("visualRole") in {"group-band", "row-band"} and "fill" in item["paint"]]
        for axis_band in axis:
            for band in bands:
                results.append((axis_band["id"], band["id"], _contrast(_composite(axis_band["paint"], canvas),
                                                                    _composite(band["paint"], canvas))))
    return results




def check_distinct_axis_band(name: str, scene: dict) -> None:
    contrasts = band_contrasts(scene)
    assert any(axis_id.startswith("axis-band") for axis_id, _, _ in contrasts) or not contrasts, name
    assert all(ratio >= MINIMUM_BAND_CONTRAST for _, _, ratio in contrasts), name


def check_bounded_axis_cells(scene: dict) -> None:
    surface = scene["surfaces"][0]
    primitives = {item["id"]: item for item in surface["primitives"]}
    axis = next(slot for slot in surface["slots"] if slot["id"] == "timeline-axis")["bounds"]
    bands = [item for key, item in primitives.items() if key.startswith("axis-band-rect:")]
    labels = [item for key, item in primitives.items() if key.startswith("axis-label:")]
    lanes = sorted({(round(band["bounds"]["block"], 3), round(band["bounds"]["blockSize"], 3)) for band in bands})
    assert len(lanes) == 1  # the packaged auto-label tier shares one year-band lane
    assert lanes[0][0] == pytest.approx(axis["block"])
    assert lanes[0][1] == pytest.approx(axis["blockSize"])
    for band in bands:
        box = band["bounds"]
        assert box["inlineSize"] > 0 and box["blockSize"] > 0
        assert box["inline"] >= axis["inline"] - 0.01
        assert box["inline"] + box["inlineSize"] <= axis["inline"] + axis["inlineSize"] + 0.01
    for label in labels:  # every label stays inside its completed painted host
        box = label["bounds"]
        host = primitives[label["hostPlacementId"]]
        assert host in bands
        assert box["inline"] >= host["bounds"]["inline"] - 0.01
        assert box["inline"] + box["inlineSize"] <= host["bounds"]["inline"] + host["bounds"]["inlineSize"] + 0.01
        lane = (host["bounds"]["block"], host["bounds"]["blockSize"])
        assert box["block"] >= lane[0] - 0.01
        assert box["block"] + box["blockSize"] <= lane[0] + lane[1] + 0.01
    by_lane: dict[float, list[dict]] = {}
    for band in bands:
        by_lane.setdefault(round(band["bounds"]["block"], 3), []).append(band["bounds"])
    for cells in by_lane.values():  # a visible gap between adjacent cells
        cells.sort(key=lambda bounds: bounds["inline"])
        assert all(right["inline"] - (left["inline"] + left["inlineSize"]) > 0.5 for left, right in zip(cells, cells[1:]))
    assert any(key.startswith("axis-separator:") for key in primitives)
    rule = primitives["axis-rule"]
    assert rule["visualRole"] == "axis-rule" and rule["bounds"]["block"] == pytest.approx(axis["block"] + axis["blockSize"])


def check_centered_fixed_axis_labels(scene: dict) -> None:
    """The fixed quarter/month fixture's centering rule, not an auto-axis policy."""
    surface = scene["surfaces"][0]
    primitives = {item["id"]: item for item in surface["primitives"]}
    for label in (item for key, item in primitives.items() if key.startswith("axis-label:")):
        host = primitives[label["hostPlacementId"]]["bounds"]
        box = label["bounds"]
        assert box["block"] - host["block"] == pytest.approx(
            host["block"] + host["blockSize"] - (box["block"] + box["blockSize"]), abs=0.01)


def check_start_aligned_month_labels(scene: dict) -> None:
    surface = scene["surfaces"][0]
    primitives = {item["id"]: item for item in surface["primitives"]}
    month_labels = [item for key, item in primitives.items()
                    if key.startswith("axis-label:") and item["text"] in {"Apr", "May", "Jun"}]
    month_cells = [item["bounds"] for key, item in primitives.items()
                   if key.startswith("axis-band-rect:3:")]
    assert month_labels
    for label in month_labels:
        cell = next(cell for cell in month_cells
                    if cell["inline"] - 2 <= label["bounds"]["inline"] <= cell["inline"] + cell["inlineSize"])
        assert label["bounds"]["inline"] - cell["inline"] > 3  # 0.5 em inset, not flush with the cell edge


def check_print_mono_greyscale(scene: dict) -> None:
    found = primitives(scene)
    # Lane Views put signed finish deltas in the member label, so they no
    # longer emit separate variance-* paint primitives. Preserve the user
    # visible slip check against those completed labels.
    deltas = [item for item in found if item.get("purpose") == "finish-delta"]
    assert not deltas  # finish deltas are composed into the lane member label
    lane_labels = [item.get("text", "") for item in found
                   if item.get("id", "").startswith("member-label:")]
    assert any(text.endswith("d") and ("+" in text or "−" in text or "-" in text)
               for text in lane_labels)
    as_of = [item for item in found if item.get("visualRole") == "as-of" and "stroke" in item["paint"]]
    grid = [item for item in found if item.get("purpose") == "axis-grid"]
    assert as_of and all(item["paint"]["dash"] for item in as_of)
    assert grid and not any(item["paint"].get("dash") for item in grid)
