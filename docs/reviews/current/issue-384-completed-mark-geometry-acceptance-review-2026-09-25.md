# Issue 384 — Completed Mark Geometry Acceptance Review

**Status:** accepted pending repository CI  
**Date:** 2026-09-25  
**Implementation:** `c06d0d9`, `177b39d`  
**Design correction:** `15bb075`

## Acceptance evidence

| Requirement | Evidence | Result |
|---|---|---|
| Theme varies marker dimensions and hatch pitch/angle without adapter source edits | Theme v0.7 structured marker/pattern values; `MarkerGeometry` and `PatternGeometry` completion; focused Scene/SVG tests. | Pass |
| Theme selects a non-diamond milestone shape | finite `symbol` token and `milestoneSymbol` role; `SymbolGeometry` expands circle, square, and chevron from completed bounds. | Pass |
| Unsupported authored treatments fail at resource boundary | Theme v0.7 schema branches plus `ThemeTokenView` typed accessors and vocabulary inventory policy. | Pass |
| Scene has completed geometry, not adapter-selected names | `ScenePrimitive.marker`, `.pattern`, and `.symbol` carry immutable geometry; `v05_svg.py` serializes supplied outlines/tile values only. | Pass |
| Default visible policy is preserved | The correction uses Layout's completed rounded diamond outline when Theme selects the default diamond. Materializer diff review found no changed point-mark paths. | Pass |
| No silent target degradation | SVG/PNG visual profiles declare completed geometry capabilities. Typst/TikZ reject surfaces containing unsupported completed treatments before output. | Pass |
| Public evidence is reproducible | Public materializer regenerated all 20 corpus slides. Generated SVG diff is limited to deterministic marker definition IDs/references and completed marker path syntax. | Pass |

## Verification

* focused renderer/Scene/capability/materializer tests passed;
* `python conformance/run_conformance.py`: PASS;
* `pytest -q`: **749 passed, 18 skipped**;
* `tools/diagnostic_inventory.py` and `tools/vocabulary_inventory.py` regenerated
  their checked reports;
* `git diff --check`: pass.

## Boundary review

The implementation preserves the Project → View → Layout → Scene → adapter
authority chain.  Theme is limited to finite appearance selection and values;
Layout retains bounds, routes, and the established rounded default point
outline; Scene completes renderer-neutral data; adapters receive no Theme or
Layout policy.  #385 can now serialize this completed model without inventing a
second mark geometry representation.

## Remaining release gate

Verify the repository CI result for `177b39d` (and this acceptance-review
commit) before closing #384.  #385 begins only after that verification.
