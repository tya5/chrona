"""Validate the derived Scene-input closure without inventing an authoring resource."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
case = yaml.safe_load((ROOT / "fixtures/presentation-scene-input-v0.1.yaml").read_text())

assert case["version"] == "chrona/presentation-scene-input/v0.1"
assert case["authority"] == "runtime-derived-only"
surfaces = {surface["id"]: surface for surface in case["inputs"]["surfaces"]}
assert set(surfaces) == {"table-timeline", "review", "minimal"}
for surface in surfaces.values():
    slots = {slot["id"]: slot for slot in surface["slots"]}
    axis = next(slot for slot in slots.values() if slot["source"] == "timeline-axis")
    timeline = next(slot for slot in slots.values() if slot["source"] == "timeline")
    assert timeline["scaleId"] == axis["scaleId"] == "primary"
    assert all(slot["bounds"] == "resolved-layout" for slot in slots.values())
    assert surface["rows"]["bounds"] == "resolved-layout"
    assert surface["primitives"]["ownership"] == "resolved-scene-geometry"
    assert surface["primitives"]["required"] == ["title-text", "axis-band", "axis-label", "tick", "comparison-mark", "item-label"]
assert set(surfaces["table-timeline"]["primitives"]["laterFamilies"]["I3-C"]) == {
    "table-frame", "table-header-band", "table-column-label", "group-surface", "group-header", "row-shade",
    "table-row-rule", "table-cell", "dependency-connector", "annotation-box", "annotation-text",
    "annotation-leader", "project-note", "legend-swatch", "legend-label", "coverage-text",
}
assert set(surfaces["review"]["primitives"]["laterFamilies"]) == {"I3-F"}
assert set(surfaces["minimal"]["primitives"]["laterFamilies"]) == {"I3-F"}
assert case["inputs"]["laneTracks"]["bounds"] == "resolved-scene-geometry"
assert set(case["inputs"]["laneTracks"]["surfaces"]) == {"row-aligned", "independent-lane-track"}
assert "adapters-receive-completed-scene-only" in case["invariants"]
assert "surface-adapter-selects-completed-primitives-only" in case["invariants"]
assert "missing-surface-or-primitive-is-a-stable-diagnostic" in case["invariants"]
assert "primitive-family-presence-is-authorized-by-surface-slot-and-visibility" in case["invariants"]
assert "routes-ports-and-text-layout-are-scene-owned" in case["invariants"]
print("presentation-scene-input derived fixture valid")
