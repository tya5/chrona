<!-- chrona:literal-acceptance/v1 -->

# Issue #1610 — on-demand member-label repair

Ready base `9d888beb7468739b68e35de8b1d0ade79cf0ff56`;
[PR #1623](https://github.com/tya5/chrona/pull/1623).
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1610#issuecomment-6227031513)
implements the [revised reviewer rule](https://github.com/tya5/chrona/pull/1623#issuecomment-6228498163).
Normative correction `aac20b479` was published before this implementation.

## Literal issue acceptance

### Issue #1610

- Source: [Issue #1610](https://github.com/tya5/chrona/issues/1610)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; a synthetic twin of the crossing case. | met | [Trace](https://github.com/tya5/chrona/issues/1610#issuecomment-6225778103); [same-inventory obstruction controls](../../../tests/unit/chrona/presentation/layout/test_member_label_route_obstruction.py), [one-retry and full-placement preservation twins](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_plan.py), and [actual stroke checks](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_stroke.py). | — |
| 2 | The two presets on the #1582 CSV draw no label crossed by a route or the as-of line, viewed as PNG. | met | Root viewed both final [CSV](https://github.com/tya5/chrona/issues/1582) PNGs in `/tmp/chrona-1610-latest-witness.mTdDbF/trace-{default,executive-light}-v4.png`. Checkout screens and Customer dashboard are visible in both; the canonical actual-width audit finds0intersections (default13names/14dependency primitives, executive11/13). No pass-1 visible label is lost. | — |
| 3 | Public SVG/Scene changes listed with counts. | not met | The prior up-front result and its39changed slides are rejected. Final on-demand implementation needs a fresh official snapshot, per-slide counts and HALCYON before/after routing measurement in [PR1623](https://github.com/tya5/chrona/pull/1623). | — |

## Programme-level criteria (optional)

Layout records route-only obstruction against each name's exact preceding
inventory. It completes an unreserved first pass and at most one repair pass;
only completed batches preserving existing labels, notes, relation status and
connected annotation topology may replace the first pass. The retry retains
the already-visible label footprints as hard routing obstacles, except names
being repaired; all names are then revalidated normally. No Scene/adapter
placement policy, project-specific branch, third trial or selective release.

The proposed ordinary-tail scheduler and broad DVT/firmware expectation
changes have been removed. DVT still uses its declared exterior fallback and
ordinary text ink rather than its former black inside position; this remaining
change is disclosed in the PR as requested. Firmware's summary remains.
The unchanged main HALCYON three-tail witness passes in
the40-test focused batch (routing, actual stroke, phase order and progress).
The revised coordinator adds13 focused preservation tests; obstruction has7
controls. These are local evidence, not release acceptance. Exact-head CI,
final PNGs/counts and the review-containing main three-OS release remain open.
