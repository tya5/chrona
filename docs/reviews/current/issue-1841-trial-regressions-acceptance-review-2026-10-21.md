<!-- chrona:literal-acceptance/v1 -->

# Issue 1841 — trial regression acceptance review

Current [work record](https://github.com/tya5/chrona/issues/1841#issuecomment-6295885856),
[approved design](https://github.com/tya5/chrona/issues/1841#issuecomment-6330996672),
and [architecture / implementation plan](https://github.com/tya5/chrona/issues/1841#issuecomment-6331069065).
Specs 08/30/38/50 retain Layout ownership of completed geometry, candidate
accounting, group identity and routes; Scene/adapters do not allocate them.
The deferred repair contract was published before source in
[`f7a2e64e5`](https://github.com/tya5/chrona/commit/f7a2e64e5eec4bca26b97b85582db1aac631fa78).

## Integrated evidence

Candidate [`9416405ec`](https://github.com/tya5/chrona/commit/9416405ecb196f1eaea08e7cbb773b7d5b61104c),
[PR 1849](https://github.com/tya5/chrona/pull/1849), includes ready main `9271af7`.
250 focused tests, 135 CLI tests and schema equivalence passed. Official snapshot
from [CI 39711731435](https://github.com/tya5/chrona/actions/runs/39711731435),
artifact `12397522751`, SHA-256
`a6d85597e1c31896e77de2c2c4105eb076335d2006b1825a5dec1805b975a07d`,
contains 50 Scenes and 50 SVGs; its six focused SVGs exactly match the locally
inspected renders. The run found an unclassified integer counter and a missing
generated Theme role reference row, corrected in
[`fa9582376`](https://github.com/tya5/chrona/commit/fa9582376).
38 counter/cursor/exchange tests and four reference tests pass after correction.
Final-head CI, complete corpus disposition and publication remain required.

Follow-up source is public on `wip/issue-1841-recovery-contract` at
[`d2559ab3a`](https://github.com/tya5/chrona/commit/d2559ab3a7bf140a688aeeb9fb1414c0e21b92e6),
including ready main `73d831833`. Test/ownership migrations and one shared
completed node-approach registration owner fix omitted stub diagnostics under
the existing contract. 54 focused tests and 50 combined integration controls
pass (overlapping sets). All six focal SVG byte streams and primitive maps
remain identical; only 02/19 add a truthful shared-approach receipt each.
The [official per-slide/receipt ledger](https://github.com/tya5/chrona/pull/1849#issuecomment-6331591571)
discloses every new recovery receipt, 32 added member names and one lost existing
name on 12-glyph-gates. Old baseline solver stages were not recorded; route
existence alone does not establish NORMAL. Previously materializable off-manifest
preset cases expose a [point-ingress/name design gate](https://github.com/tya5/chrona/issues/1841#issuecomment-6331475701).
Do not waive those tests or introduce another scheduling rule while awaiting
its disposition. Canonical PR 1849 remains at 9416405ec with failed CI; its
derived-ready failure follows the failed conformance/pytest prerequisites.

HALCYON 02/11/19 retain all previous member-name identities/text and add Launch
and Pre-ship review (20 to 22 names each). 16 retains all 26, including Launch
services confirmed, Ground station upgrade and Bus functional test. All logical
relations remain in the six focused contexts (24/24/25/24/25/10). Root inspected
actual SVG previews 02/16/25 and roadmap Sunday: Launch is visible and the
station/signoff note tails retain their connected geometry.

Fresh trial 12 uses published inputs
[`81d11c3c`](https://github.com/tya5/chrona/tree/81d11c3cb6823d1b4ddae6a4659db7f4a8d75de6/trial-12):
matching w2 Scene, w3 Actual, w0 Snapshot, forecast and explicit preset locale.
All six renders succeed. Each preset's plain/hinted w3 maps of **all 255 Path
and 197 Text primitives** are exactly equal. Each hint summary has 107 relations:
75 accepted/revalidated, 32 invalidated/searched, zero absent/unusable. Concurrent
wall observations (two workers, whole seconds) are target-b/en-US 28/29/22 s and
yuya/ja-JP 29/29/23 s for w2/plain/hinted, not a performance guarantee.

Fresh trial 16 uses published inputs
[`88781e7e`](https://github.com/tya5/chrona/tree/88781e7eafa331be04fb69154e161d5727b31497/trial-16):
v1 project + yuya/ja-JP; v2 adds Actual and baseline Snapshot, no forecast.
Both succeed, retain 20 logical relations and have 228/296 primitives.
Root inspected both actual SVG previews, r08's identical route/opaque-halo
point arrays, and its marks-stage receipt. The note leader has explicit fallback
diagnosis. The observer reports zero errors/warnings; this is not a NORMAL
temporal-hull or critical-temporal-excursion claim. Removed axis decorations
follow #1855. Three finished-Actual progress fills and their key are also absent
on ready main, per [Spec 61](../../specification/61-progress-fill-marks.md) and
approved [`086f4851`](https://github.com/tya5/chrona/commit/086f4851d70077c2cf13d9ea9b490892783a55c5).

## Literal issue acceptance

### Issue #1841

- Source: [issue body and later criteria](https://github.com/tya5/chrona/issues/1841)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | hints validate against the completed host geometry whatever the primitive kind. On the trial input, hinted renders accept the unchanged routes and the time drops (before/after recorded). | met | [Host controls](../../../tests/unit/chrona/usecases/test_previous_scene.py), [original before/after timing audit](https://github.com/tya5/chrona/issues/1841#issuecomment-6296684466), integrated trial 12 above; released on review-containing main `4e779217` / [CI 39553831077](https://github.com/tya5/chrona/actions/runs/39553831077). | — |
| 2 | one shared measure/place rounding for every content-width text; a synthetic case for cells and headers. | met | [Fractional header/cell controls](../../../tests/unit/chrona/presentation/layout/test_table_forward_fit.py); released on review-containing main `4e779217` / CI 39553831077. | — |
| 3 | the title is honoured; the guide example runs on the default preset in the docs tests. | met | [Actual SVG headings](../../../tests/integration/test_network_heading_parts.py), [executable guide](../../../tests/integration/test_network_view_guide.py); released on review-containing main `4e779217` / CI 39553831077. | — |
| 4 | a route segment may not run along a mark's edge (treat edge contact as an obstacle); a synthetic case. | not met | [Published closed-contact tests](https://github.com/tya5/chrona/blob/d2559ab3a7bf140a688aeeb9fb1414c0e21b92e6/tests/unit/chrona/presentation/layout/test_primary_mark_closed_contact.py), official snapshot and visual evidence above. Final-head CI, complete corpus disposition and review-containing-main release remain required. | — |
| 5 | network rank placement keeps unchanged nodes (hint or stable ordering), and row pitch is quantised so rows above an insertion stay byte-identical. | met | By [approved contract](https://github.com/tya5/chrona/issues/1841#issuecomment-6297232443): fractional authored pitch/fill redistribution and rank-demand movement remain intentional. [Spec 33](../../specification/33-intent-oriented-layout.md), [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md); no rounding, new node hints or preset tuning. | — |
| 6 | a route's horizontal extent stays within its endpoints' times plus the port leads, unless it is diagnosed as recovery. | not met | [Published temporal-hull tests](https://github.com/tya5/chrona/blob/d2559ab3a7bf140a688aeeb9fb1414c0e21b92e6/tests/unit/chrona/presentation/layout/test_relation_endpoint_geometry.py), integrated trial 16 above. Final corpus/release evidence remains required. | — |

## Programme-level criteria (optional)

Keep issue open until complete corpus changes and every HALCYON
NORMAL-to-recovery transition are reviewed, final PR checks pass, and exact
published main containing this review passes three-OS release CI. No safety
waiver, new quota, corpus adaptation or further scheduling rule is authorized.
