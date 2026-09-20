"""Validate the G2--G4 design cases; this is not a renderer test."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
case = yaml.safe_load((ROOT / "fixtures/presentation-g2-g4-design-v0.1.yaml").read_text())

assert len(case["positive"]["projects"]) == 2
assert any(len(label["text"]) >= 48
           for project in case["positive"]["projects"] for label in project["labels"])
assert any(annotation["anchor"]["facet"] == "actual"
           for project in case["positive"]["projects"] for annotation in project["annotations"])
assert all(annotation["anchor"]["kind"] == "object"
           for project in case["positive"]["projects"] for annotation in project["annotations"])
assert all(project["routing"]["limit"] > 0 for project in case["positive"]["projects"])
assert {project["laneSurface"] for project in case["positive"]["projects"]} == {"row-aligned", "independent-lane-track"}
assert all(project["pitchPolicy"] == "scene-mark-extent-plus-clearance" for project in case["positive"]["projects"])

expected = {"E_PRESENTATION_LABEL_UNPLACEABLE", "E_PRESENTATION_ANCHOR_MISSING",
            "E_PRESENTATION_ANCHOR_UNSUPPORTED", "E_PRESENTATION_STACK_OVERFLOW",
            "E_PRESENTATION_ROUTE_LIMIT"}
assert {entry["diagnostic"] for entry in case["negative"]} == expected
assert case["negative"][0]["input"]["maxCandidates"] > 16
assert case["negative"][-1]["input"]["routing"]["limit"] < 1
print("G2-G4 design fixture valid: two generic projects, long English text, missing actual, and five negative diagnostics")
