<!-- chrona:literal-acceptance/v1 -->

# Issue #1610 — paint-safe member-label reservations

Product `ec4f5ecf1a208088234a99d9712b14bfda1790d2`, based on ready main
`8c4d17f917b29600fd72e5b514ad06d31242ca33`; [PR #1623](https://github.com/tya5/chrona/pull/1623).
Follow-up `aa02fe2f3` fixes optional reservation failure and updates isolated
controls/test-fixture outputs: 67 focused tests pass. A fresh public snapshot
and current-head release evidence remain required; the counts below describe
the initial product artifact, not a later head.
[Living design/architecture/implementation record](https://github.com/tya5/chrona/issues/1610#issuecomment-6227031513).
Specs 33/38/50 precede each product correction. Layout alone owns reservations,
required-label identity, bounded retries, routing and actual-paint validation;
Scene/adapters add no policy. Candidate order, association, quality limits and
explicit unsafe terminal modes remain unchanged. The duplicate lane planner is removed.

## Literal issue acceptance

### Issue #1610

- Source: [Issue #1610](https://github.com/tya5/chrona/issues/1610)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; a synthetic twin of the crossing case. | met | [Public trace](https://github.com/tya5/chrona/issues/1610#issuecomment-6225778103); [real-owner reservation twin](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_plan.py), [required/rule controls](../../../tests/unit/chrona/presentation/layout/test_member_label_required_phase.py), [bounded channel controls](../../../tests/unit/chrona/presentation/layout/test_relation_shapes.py), [paint/terminal-completion regression](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_stroke.py), and [actual rule widths](../../../tests/unit/chrona/presentation/layout/test_surface_obstacle_seed.py). Combined focused batch: 158 passed. | — |
| 2 | The two presets on the #1582 CSV draw no label crossed by a route or the as-of line, viewed as PNG. | met | Root rendered and viewed both product PNGs from the unchanged [public CSV/Actual](https://github.com/tya5/chrona/issues/1582): `/tmp/chrona-1610-acceptance-75J1TZ/{default,executive-light}-final.png`. Both requested names remain visible. Audit of every completed member-name box against actual-width dependency/as-of paths finds zero intersections: default 13 visible names/14 dependency primitives; executive-light 11/13. Executive's two other suppressed names are API design/UI mockups. | — |
| 3 | Public SVG/Scene changes listed with counts. | met | Official [snapshot12083134379](https://github.com/tya5/chrona/actions/runs/38988103045/artifacts/12083134379): 109 before/after paths, none added/retired; 39 SVG + 39 Scene changed, 11 + 11 byte-identical. [PR body](https://github.com/tya5/chrona/pull/1623) gives each changed slide's changed/removed/added route, Text, other primitive and diagnostic counts. No relation primitive is removed or added; all five HALCYON targets 21–25 are byte-identical. No bot-owned example output is authored; the follow-up regenerates 14 authored test-fixture output files only. | — |

## Programme-level criteria (optional)

Release disposition: not accepted. Initial CI38988103045 failed all three pytest
shards (34 failures); conformance and reproduction passed. Repairs address an
optional reservation applying final visible-overflow failure, progress/ownership
expectations, isolated phase/route-entry controls and generated test fixtures.
The shared CLI golden awaits coordination with PR1615; it is not edited here.
Current-head CI and exact review-containing main three-OS release are required.

An architectural acceptance gap remains: the accepted #466 candidate-placement
design requires HALCYON02's three selected Project notes to retain connected plot
tails. The new route inventory makes station-note exhaust its existing search
and select plot-no-tail. Its test remains unchanged and failing. Reviewer
[disposition requested](https://github.com/tya5/chrona/pull/1623#issuecomment-6227761562):
adapt existing declarative candidates atomically, or explicitly review a design
change; no project-specific core exception or silently weakened witness.
The controller DVT inside-label and firmware-slip summary witnesses also need
explicit disposition. No annotation policy correction is inferred from a golden
refresh. The disclosed public tradeoffs also await review:
launch-campaign loses three ordinary names; some annotation note-index text and
one tvac-slip relation label disappear while other names return. These are not
hidden by corpus edits or accepted merely because tests pass.

Sequential isolated HALCYON programme-board profiles, same input: routing
1 call/0.493 s on ready main → 3 calls/8.253 s on product; whole profiled
materializer 2.986 → 11.143 s, wall 3.65 → 12.00 s. Reserved inventories cause
more bounded graph searches (12 → 125 builds); the first-fit supplement is not
used by this best-policy slide. These are measurements, not a borrowed target.
Cross-trial graph reuse is not assumed safe across different inventories.
