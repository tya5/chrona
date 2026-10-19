# Issue 1754 — revision stability acceptance

Status: all four literal criteria have implementation evidence; publication
of this follow-up and its exact-main three-OS release remain required.
Implementation landed in [1769](https://github.com/tya5/chrona/pull/1769).
Rows 1–3 are released on
[39256723703](https://github.com/tya5/chrona/actions/runs/39256723703),
exact `9dca9c55a8df0d1e44149a0543fe892366d39930`.
Current [work record](../../planning/active/issue-1754-revision-stability-work-record-2026-10-19.md).

| # | Literal acceptance criterion | Status and direct evidence |
| ---: | --- | --- |
| 1 | Synthetic: removing one relation and appending another keeps every other relation's primitive id; hints are accepted for all unchanged relations. | Met and released: `tests/integration/test_revision_relation_identity.py`, first-fit and best; anonymous and duplicate identity tests. Reviewer acceptance [6268761101](https://github.com/tya5/chrona/issues/1754#issuecomment-6268761101). |
| 2 | target-b with `--previous-scene` uses the hints (receipts show accepted hints), or reports why not. | Met and released. The current full trial accepts 110 target-b relation-instance hints across weeks 2–5; all other attempts have invalidated, unusable or absent dispositions. |
| 3 | A synthetic slip that does not touch a relation's endpoints keeps that relation's route; no new through-mark crossing appears where a detour exists. | Met and released: `tests/integration/test_revision_route_corridor.py`, both policies, unchanged endpoints, retained corridor, obstructed-hint negative twin and actual mark-clear replacement path. |
| 4 | Re-running trial 8 with hints: the changed-primitive count of unchanged objects falls, and the table is posted on the issue. executive-light labels of unchanged tasks do not toggle with the as-of line. | Met in the full rerun below: raw changes 932 → 930; row-normalized changes 323 → 315. Issue table linked below. The controlled as-of invariant covers six line positions in six placement modes; unrelated label toggles are not described as resolved. Follow-up release pending. |

## Full trial evidence

Product base `d0dc06f6bc17227cda31cb9df8fbd7dc2dc3077c`; source
`0270cddd19ac2f58abf7d51dc2529cf441105df0` adds only controlled tests and this
review. Inputs exported unchanged from public
[`bf3940dbe9af487ac6cace5458554762594f3477`](https://github.com/tya5/chrona/tree/bf3940dbe9af487ac6cace5458554762594f3477/trial-8).
All **27** actual PNG/Scene renders return process success, application
`status=ok`, and both artifacts. Three design pipelines run concurrently;
weeks and previous-Scene chains remain sequential. Identical week 1 is reused.
Week 5 retains forecast and now succeeds after 1766; no input, preset, search
budget, validator or forecast flag was changed to make this trial pass.

The full table is [posted on the issue](https://github.com/tya5/chrona/issues/1754#issuecomment-6279258773).
Counts sum all four consecutive-week transitions, comparing plain and hinted
renders on the **same candidate**, not legacy ID renumbering. Exact per-pair
counts, label identities, input/output hashes and reproduction commands:
[trial summary](assets-1754/trial-summary.json).

| Design | Raw changed primitives, plain → hint | Row-normalized changes, plain → hint | Added / removed, plain → hint | Unchanged-task label toggles, plain → hint |
| --- | ---: | ---: | --- | ---: |
| executive-light | 259 → 263 | 108 → 103 | 112 / 45 → 110 / 44 | 37 → 34 |
| target-b | 331 → 331 | 102 → 103 | 38 / 1 → 38 / 1 | 0 → 0 |
| marquee | 342 → 336 | 113 → 109 | 38 / 2 → 38 / 2 | 0 → 0 |
| Total | 932 → 930 | 323 → 315 | 188 / 48 → 186 / 47 | 37 → 34 |

Including additions/removals gives 1168 → 1163 changed primitive instances.
This is a small aggregate improvement, **not** a claim that every design or
transition improves. Row normalization removes row translation; it is not the
raw metric. Week 5 switches to forecast, so its source-unchanged objects may
have changed projected schedule/paint; these are counted, not filtered out.

Hint receipts: executive-light 354 accepted / 168 invalidated / 158 unusable /
10 absent; target-b 110 / 77 / 153 / 5; marquee 98 / 83 / 159 / 5.
The existing best/first-fit validation and safety rules are retained.

The line-only invariant is isolated by `7e1234689`: required, final and
reserve-only labels, each with/without a fixed blocking route, across six line
positions inside/outside the actual text footprint. Full placement batches
and all non-line obstacles remain identical. Final labels still avoid the
fixed route; reservations retain the existing route-free policy. Both
member-label unit modules pass **38 tests** on the rerun base.
The full trial changes routes, rows and forecast state too; its 34 remaining
executive-light label toggles are not evidence that the as-of line suppressed
them. No blanket all-label stability promise is added.

Actual adapter PNGs inspected: executive-light hinted week 3 and
[week 5](assets-1754/executive-light-w5.png),
[target-b hinted week 5](assets-1754/target-b-w5.png), and
[marquee hinted week 5](assets-1754/marquee-w5.png).
The as-of decoration, forecast/baseline marks and legend are present; Inventory
reservation is drawn across the line. The batch reports zero text/text
overlaps and no clipped text in all 30 scenes (27 renders plus reused week 1).
Dense route crossings and existing contrast warnings remain visible and are
not waived by this acceptance.

## Architecture and public release

Core owns canonical relation identity; Layout owns validated hint reuse and
the exact as-of exclusion for member labels; Scene transports completed
cone-ground policy; adapters infer none of these. The 1754 follow-up itself
changes no product policy, schema, preset or generated public output.
PR1786 also carries the independently reviewed
[1756 colour checks](issue-1756-colour-customisation-acceptance-review-2026-10-20.md)
and [416 network intent](issue-416-network-view-acceptance-review-2026-10-20.md);
their contracts and combined snapshot are reviewed separately. The zero-change
snapshot below proves the 1754 slice, not every later integrated change.

Follow-up official snapshot: [39339520912](https://github.com/tya5/chrona/actions/runs/39339520912),
source `693c3eb38c5649ead1ce26091167128b291a70ea`, artifact `12227948859`, ZIP SHA256
`64ba4c09c8ae198ad13d304943faf979acc289df010d6f347335a5f6d19bcd13`.
All 109 before/after paths are byte-identical (50 SVG, 50 Scene, 9 reports);
zero changes or retirements. All validation/test jobs pass; only the exact-base
gate fails after reviewer1785 advances main. That guard is retained; final CI
must follow the next coordinated ready main before landing.

The original PR's official snapshot
[39174351117](https://github.com/tya5/chrona/actions/runs/39174351117)
changed 50 SVG and 50 Scene files, retired none; after canonical-ID matching,
8 route point lists and 37 member-label placements changed, with 11 labels
added and 4 removed. The
[per-path summary](assets-1754/public-snapshot-summary.json) and existing
public before/after PNGs retain that evidence. The old locale-wheel failure
is superseded by successful exact-main release 39256723703, not ignored.

The issue remains open until this follow-up review and controlled tests land
and the required full three-OS/conformance/wheel/newest-Python release succeeds
on their exact published main. The integrated candidate passes 532 focused
tests across all three slices, including this issue's controlled labels.
Full pytest is delegated to CI.
