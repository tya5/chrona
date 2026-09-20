#!/usr/bin/env python3
"""Validate design-to-use-case-to-milestone traceability without product runtime code."""
from pathlib import Path
import re

import yaml

DOCS = Path(__file__).resolve().parents[1] / "docs"
MATRIX = yaml.safe_load((DOCS / "traceability" / "design-usecase-milestone-v0.1.yaml").read_text())
CATALOG = (DOCS / "specification" / "14-use-case-catalog.md").read_text()
ROADMAP = (DOCS / "planning" / "active" / "product-delivery-roadmap.md").read_text()


def fail(message: str) -> None:
    raise SystemExit(f"Traceability: FAIL: {message}")


if MATRIX.get("version") != "chrona/design-traceability/v0.1":
    fail("unexpected matrix version")

areas = MATRIX["areas"]
findings = MATRIX["findings"]
area_ids = [area["id"] for area in areas]
finding_ids = [finding["id"] for finding in findings]
if len(area_ids) != len(set(area_ids)):
    fail("duplicate area ID")
if len(finding_ids) != len(set(finding_ids)):
    fail("duplicate finding ID")

catalog_use_cases = set(re.findall(r"^### (UC-\d{2}) —", CATALOG, re.MULTILINE))
summary_use_cases = set(re.findall(r"^\| (UC-\d{2}) \|", CATALOG, re.MULTILINE))
roadmap_milestones = set(re.findall(r"^\| (M\d+(?:\.\d+)?) —", ROADMAP, re.MULTILINE))
matrix_use_cases: set[str] = set()

for area in areas:
    use_cases = set(area["useCases"])
    milestones = set(area["milestones"])
    matrix_use_cases.update(use_cases)
    if area["productFacing"] and (not use_cases or not milestones or not area["evidence"]):
        fail(f"incomplete product-facing area {area['id']}")
    missing_catalog = use_cases - catalog_use_cases
    missing_summary = use_cases - summary_use_cases
    missing_roadmap = milestones - roadmap_milestones
    if missing_catalog:
        fail(f"{area['id']} missing detailed use cases {sorted(missing_catalog)}")
    if missing_summary:
        fail(f"{area['id']} missing summary use cases {sorted(missing_summary)}")
    if missing_roadmap:
        fail(f"{area['id']} missing roadmap milestones {sorted(missing_roadmap)}")

if catalog_use_cases != summary_use_cases:
    fail("catalog detailed and summary use-case sets differ")
if catalog_use_cases != matrix_use_cases:
    fail("catalog and matrix use-case sets differ")
for finding in findings:
    if finding["status"] != "closed" or not finding.get("closedBy"):
        fail(f"finding remains open: {finding['id']}")

print(f"Traceability: PASS ({len(areas)} areas, {len(catalog_use_cases)} use cases, {len(roadmap_milestones)} milestones)")
