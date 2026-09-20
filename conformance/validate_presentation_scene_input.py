"""Validate the derived Scene-input closure without inventing an authoring resource."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
case = yaml.safe_load((ROOT / "presentation-scene-input-v0.1.yaml").read_text())

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
assert case["inputs"]["primitivePayloads"]["Text"] == ["text", "textLayout"]
assert case["inputs"]["primitivePayloads"]["Rect"] == ["bounds", "optionalCornerRadius"]
assert case["inputs"]["primitivePayloads"]["connectorPath"] == ["points", "fromPortId", "toPortId"]
assert case["inputs"]["comparisonMarkMetadata"] == ["laneGroupId", "stackIndex"]
assert set(case["inputs"]["conditionalFamilies"]) == {"missingActual", "variance", "annotation", "summary"}
assert "primitive-kind-payload-mismatch-is-a-stable-diagnostic" in case["invariants"]
content = case["inputs"]["surfaceContentInput"]
assert content["adapterVisible"] is False
assert set(content["required"]) == {"tableColumns", "tableCells", "relations", "annotations", "notes", "legendEntries", "coverageText", "summaryPanels", "templateValues"}
assert content["templateValues"] == ["title", "windowStart", "windowLastVisible", "selectedCount", "unmatchedCount", "missingCount"]
assert content["summaryPanelShape"] == ["panelId", "headingText", "orderedMetricPairs"]
assert content["summaryMetricShape"] == ["metricId", "formattedText"]
review_slots = surfaces["review"]["slots"]
assert any(slot.get("optional") is True and slot["source"] == "summary-or-other-authorized-optional-source"
           for slot in review_slots)
assert "adapters-never-read-surface-content-input" in case["invariants"]
manifest = case["inputs"]["manifest"]
assert manifest["version"] == "chrona/presentation-scene-manifest/v0.1"
assert manifest["authority"] == "derived-inspection-only"
assert manifest["required"] == ["settingsVersion", "viewport", "selectedObjectIds", "fontAssetIdentities",
                                "contentFamilyCounts", "surfaceScales"]
assert manifest["viewport"] == ["width", "height"]
assert manifest["contentFamilyCounts"] == ["relations", "annotations", "notes", "legendEntries", "summaryPanels"]
assert manifest["surfaceScaleShape"] == ["surfaceId", "scaleId", "domainStart", "domainEnd", "rangeStart",
                                           "rangeEnd", "origin", "unitRatio"]
assert manifest["surfaceOrder"] == ["table-timeline", "review", "minimal"]
assert manifest["adapterBoundary"] == "identical-scale-record-on-selected-scene-surface"
assert case["inputs"]["diagnostics"]["successfulInitialProfile"] == []
assert "manifest-is-derived-and-non-authoritative" in case["invariants"]
assert "adapters-preserve-surface-scale-record-without-reconstruction" in case["invariants"]
assert "consumption-proof-uses-trigger-fixtures" in case["invariants"]
assert "v0.2-settings-layout-is-not-shadowed-by-v0.1-profile" in case["invariants"]
print("presentation-scene-input derived fixture valid")
