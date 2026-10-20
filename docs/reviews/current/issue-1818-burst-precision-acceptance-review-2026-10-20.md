# Issue 1818 — declared burst precision

Status: implementation and official artifact verified; exact-main release pending.
Base: trusted ready `ec8f27ed3`; published design `6bbb74f49`; source `496717707`.
[Current design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1818#issuecomment-6288189726).

| Literal acceptance criterion | Verdict | Evidence |
| --- | --- | --- |
| Resolve the macOS materializer failure with a general, documented rule at its responsible layer; no project-specific branch or hand-edited evidence. | met | Layout applies declared `scenePrecision`; fresh published-code macOS and official Linux `roadmap-sunday` Scenes are byte-identical, SHA256 `e7b71fe9d03bc64ff144736f5e95946aa321473236b9dd65d2333af7f567f7c1`. No platform branch, tolerant comparison, trig kernel or authored derived files. Exact-main release remains pending. |
| Add a focused synthetic regression and retain burst padded-text containment and geometry validation. | met | `test_chip_scene_precision.py` (8 tests) and `test_burst_scene_precision.py` (6 real pinned-Context circle/ellipse × 0/3/6 cases); chip/as-of/lane/render-plan batch 76 passed. Tests include subquantum perturbation, explicit half-even, arbitrary high precision, preserved bounds, text coverage and truthful precision refusal. |
| Verify actual declared roadmap-sunday output and exact-main three-OS release; disclose any intended Scene/SVG differences. | not met | Exact published-head macOS output `/tmp/chrona-1818-exact-dbb-roadmap.8Ma2Qz/review.scene.json` matches the official Linux after-tree below. Old evidence mismatch is expected until bot publication. The all-slide audit is complete; required exact-main three-OS release is still pending. |

Official PR run [39404525656](https://github.com/tya5/chrona/actions/runs/39404525656),
head `dbb985b9115543bb0dc392199943a4411af830ee`, artifact `12255449113`,
SHA256 `611969ad5dc30b4d82c22b5f881dc51c48593b26ae22633e26ee0303da4d48f3`:
109 identical path names, zero additions/retirements; 48 SVG/Scene pairs unchanged.

| Changed slide | Primitives | Paths (geometry changed) | Text (geometry changed) | Added/removed IDs, text-content changes, diagnostic changes |
| --- | --- | --- | --- | --- |
| chrona-roadmap/roadmap-sunday | 277→277 | 18→18 (14) | 109→109 (84) | 0 |
| halcyon-1/25-sunday | 354→354 | 49→49 (39) | 122→122 (84) | 0 |

Only those two SVG/Scene pairs change: existing float geometry moves by at most
0.001 with the declared precision/reservation; paint roles and primitive kinds
remain unchanged. Contrast-report differences are only sample coordinates
(verified after removing that column); ratios, floors and severity stay equal.
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
Issue stays open until the pending literal release evidence is complete.
