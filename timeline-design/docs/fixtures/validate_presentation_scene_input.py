"""Validate the derived Scene-input closure without inventing an authoring resource."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
case = yaml.safe_load((ROOT / "fixtures/presentation-scene-input-v0.1.yaml").read_text())

assert case["version"] == "chrona/presentation-scene-input/v0.1"
assert case["authority"] == "runtime-derived-only"
slots = {slot["id"]: slot for slot in case["inputs"]["slots"]}
assert {"table", "timeline", "timelineAxis"} <= slots.keys()
assert slots["timeline"]["scaleId"] == slots["timelineAxis"]["scaleId"] == "primary"
assert all(slot["bounds"] == "resolved-layout" for slot in slots.values())
assert case["inputs"]["rows"]["bounds"] == "resolved-layout"
assert case["inputs"]["laneTracks"]["bounds"] == "resolved-scene-geometry"
assert set(case["inputs"]["laneTracks"]["surfaces"]) == {"row-aligned", "independent-lane-track"}
assert "adapters-receive-completed-scene-only" in case["invariants"]
print("presentation-scene-input derived fixture valid")
