# Architecture Review — #467 lane-count acceptance rebaseline

**Reviewed:** [design correction](../../design/issue-467-494-lane-count-acceptance-correction-2026-09-27.md), [design plan](../../planning/active/issue-467-494-l3-lane-count-acceptance-rebaseline-design-plan-2026-09-27.md), [Specifications 38](../../specification/38-review-row-composition.md), [46](../../specification/46-completed-scene-paint.md), and [50](../../specification/50-constraint-driven-gantt-surface-quality.md). **Public design base:** `0f7d8cef9789927d2360587dbe18dcda8b2f102f`. **Conclusion:** accepted for implementation planning; no product code is authorized by this review alone.

## Whole-architecture consistency

| Boundary or adjacent design | Finding |
| --- | --- |
| Project, selected 4wd schedule and immutable comparison/Actual | The numeric gate does not alter dates, baseline or Actual. The existing named-chain data correction remains required. |
| View v0.27, #486 attached milestones and #498 preset defaults | Count only selected root/attached items once, while comparison/Actual are facets; lane default and packaged-resource migrations remain coupled at L3c. Editorial reference stays a separate gallery identity under its published correction. |
| Theme, icon geometry and Specifications 38/46 | Keep resolved icon/font metrics and conservative target-independent 10× path extent in Layout. A relaxed numeric ceiling is not permission to omit marks, labels or stroke. |
| Layout preflight, #480/#481/#487 and #466/Specification 50 | One immutable plan owns lane membership, natural height, table rows, group bands and phase-one required-label obstacles. Above-ten causes come from measured conflicts in that plan. Third-row use is deterministic but optional for acceptance. |
| Scene, adapters and #494 routes | Scene never derives lane/collision causes or repairs routes; adapters only serialize. Required labels remain obstacles; suppression causes and no-crossing criteria are unchanged. |
| Public evidence and reviews | WIP 13 lanes is a feasibility lead, not current-main proof. Final rendered slides, materializer batch, CI and literal acceptance table remain necessary. Earlier reviews are historical and superseded on the threshold only. |

## Risks and disposition

The conservative path envelope may produce a higher current-main count than the WIP report. The optional third row can trade fewer lanes for taller rows and more route-quality rejection. Both are measured at B2/B3 rather than hidden by conditionals. If the fourteen-lane chain/attribution gate or route-label gate fails, return to design and publish a correction before activation. The clean boundary is preserved: no new View field, Scene route policy, adapter-specific geometry, or compatibility shim is justified.

**Next:** publish an implementation-plan amendment changing L3b's pause condition and adding the source-keyed above-ten inventory and early WIP/current-main feasibility distinction. S2b mapping may proceed independently of the numeric gate.
