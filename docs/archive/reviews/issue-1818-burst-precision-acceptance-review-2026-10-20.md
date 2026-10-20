# Issue 1818 — declared burst precision

Status: accepted and closed; all three literal rows and exact-main release complete.
Base: trusted ready `ec8f27ed3`; published design `6bbb74f49`; source `496717707`.
[Current design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1818#issuecomment-6288189726).

| Literal acceptance criterion | Verdict | Evidence |
| --- | --- | --- |
| Resolve the macOS materializer failure with a general, documented rule at its responsible layer; no project-specific branch or hand-edited evidence. | met | Layout applies declared `scenePrecision`; fresh published-code macOS and official Linux `roadmap-sunday` Scenes are byte-identical, SHA-256 `e7b71fe9d03bc64ff144736f5e95946aa321473236b9dd65d2333af7f567f7c1`. No platform branch, tolerant comparison, trig kernel or authored derived files. |
| Add a focused synthetic regression and retain burst padded-text containment and geometry validation. | met | `test_chip_scene_precision.py` (8 tests) and `test_burst_scene_precision.py` (6 real pinned-Context circle/ellipse × 0/3/6 cases); chip/as-of/lane/render-plan batch 76 passed. Tests include subquantum perturbation, explicit half-even, arbitrary high precision, preserved bounds, text coverage and truthful precision refusal. |
| Verify actual declared roadmap-sunday output and exact-main three-OS release; disclose any intended Scene/SVG differences. | met | Final PR artifact and actual SVG visual review below disclose the two geometry-only pairs; exact review-containing main `27d2fd8f203ed28abc1f293a4d77674958aab92a` passed [release39410064482](https://github.com/tya5/chrona/actions/runs/39410064482) on all three OS, including full pytest/conformance/wheel, MCP floor and newest-Python reproduction. |

Final PR run [39407084677](https://github.com/tya5/chrona/actions/runs/39407084677),
head `8ed385626`, artifact `12257333511`, SHA-256
`e7e8347e997281cf2782039492bac5ef9ebd2d3c8ec722ccda3a56145614da2f`:
109 identical path names, zero additions/retirements; 48 SVG/Scene pairs unchanged.

| Changed slide | Primitives | Paths (geometry changed) | Text (geometry changed) | Added/removed IDs, text-content changes, diagnostic changes |
| --- | --- | --- | --- | --- |
| chrona-roadmap/roadmap-sunday | 277→277 | 18→18 (14) | 109→109 (84) | 0 |
| halcyon-1/25-sunday | 354→354 | 49→49 (39) | 122→122 (84) | 0 |

Only those two SVG/Scene pairs change: existing float geometry moves by at most
0.001 with the declared precision/reservation; paint roles and primitive kinds
remain unchanged. Independent raster comparison found changed pixels at 0.087%
and 0.053% respectively; root and independent visual review found no clipping,
text loss, or ground loss. Contrast-report differences are only sample
coordinates (verified after removing that column); ratios, floors and severity
stay equal. This final PR artifact has an identical 109-path after-tree to the
previously audited artifact.
Inventory changes are source anchors and two chip-ground guard catalog entries.

Architecture review (root + independent Luna): existing Context precision flows
through render plan/request, as-of and fixed-lane premeasurement into one Layout
chip completion. Measurement retains the original fit and reserves half-quantum
displacement; final bounds enclose snapped ink and padded-text coverage is checked.
Rectangle/catalogue geometry stays unquantized. Scene/adapters only project the
completed result. No public schema, version, identity or fallback change.
Float-accumulation, inward-import and explicit Scene-delivery checks pass.
First-head CI `39404525656` passed shards 1/2, conformance and public materializers;
shard 3 found one stale exact preflight-keyword expectation, now corrected with
precision 3/6 coverage. The affected 29/69-test batches pass (overlapping suites).
No product code changes follow the audited `dbb985b91` head.
CI owns generated reports/materializers and full suites; no duplicate local full run.
[Closing acceptance](https://github.com/tya5/chrona/issues/1818#issuecomment-6289995830)
confirms every literal row after the exact-main release, not on PR checks alone.
