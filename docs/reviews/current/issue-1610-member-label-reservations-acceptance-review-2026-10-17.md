<!-- chrona:literal-acceptance/v1 -->

# Issue #1610 — on-demand member-label repair

Ready base `9d888beb7468739b68e35de8b1d0ade79cf0ff56`;
[PR #1623](https://github.com/tya5/chrona/pull/1623).
[Current design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1610#issuecomment-6227031513)
implements the [revised reviewer rule](https://github.com/tya5/chrona/pull/1623#issuecomment-6228498163).
Product `712e7240f`; Specs33/50 correction `450771caa` was published before
the repair-only channel implementation.

## Literal issue acceptance

### Issue #1610

- Source: [Issue #1610](https://github.com/tya5/chrona/issues/1610)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Trace posted; a synthetic twin of the crossing case. | met | [Trace](https://github.com/tya5/chrona/issues/1610#issuecomment-6225778103); [same-inventory obstruction controls](../../../tests/unit/chrona/presentation/layout/test_member_label_route_obstruction.py), [one-retry and full-placement preservation twins](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_plan.py), and [actual stroke checks](../../../tests/unit/chrona/presentation/layout/test_surface_route_label_stroke.py). | — |
| 2 | The two presets on the #1582 CSV draw no label crossed by a route or the as-of line, viewed as PNG. | met | Root viewed both final [CSV](https://github.com/tya5/chrona/issues/1582) PNGs in `/tmp/chrona-1610-current-matrix.1xD6Q4/{default,executive-light}.png`. Checkout screens and Customer dashboard are visible in both; the canonical actual-width audit finds0intersections (default13names/14dependency primitives, executive11/13). No pass-1 visible label is lost. | — |
| 3 | Public SVG/Scene changes listed with counts. | met | [PR1623](https://github.com/tya5/chrona/pull/1623) lists every changed slide and routing measurement from [exact-head5210e849d artifact12087258176](https://github.com/tya5/chrona/actions/runs/38997760447/artifacts/12087258176): 109paths, none added/retired; SVG32changed/18identical; Scene34changed/16identical. No dependency primitive removed. Root viewed eight before/after PNG pairs; five approved HALCYON targets have no primitive/diagnostic changes. | — |

## Programme-level criteria (optional)

Layout records route-only obstruction against each name's exact preceding
inventory. Its first pass retains the existing policy-specific phases and
best/lane corridor preflight, followed by at most one new repair pass;
only completed batches preserving existing labels, notes, relation status and
connected annotation topology may replace the first pass. The retry retains
the already-visible label footprints as hard routing obstacles, except names
being repaired; all names are then revalidated normally. No Scene/adapter
placement policy, project-specific branch, extra repair trial or selective release.
Only actual repair-obstacle identities enable the bounded channel supplement;
ordinary first-fit retains its original proposals without probing that helper.

The proposed ordinary-tail scheduler and broad DVT/firmware expectation
changes have been removed. DVT still uses its declared exterior fallback and
ordinary text ink rather than its former black inside position; this remaining
change is disclosed in the PR as requested. Firmware's summary remains.
The unchanged main HALCYON three-tail witness passes in the final93-test
batch (routing, actual stroke, phases, materializers, alias, dates and CLI).
Real route-only/mixed-blocker attribution has11 passing controls; the final
coordinator identity/repair-only checks add13 passing controls. Sequential
HALCYON cProfile: main1call/0.546s routing, product2calls/9.955s; total
profile3.096s→12.778s, wall3.153s→13.019s. Cost remains high and is disclosed,
not described as improved. Public differences include labels lost or exchanged
on HALCYON01/03 and the programme-board family; these are disclosed in the PR,
not hidden by example edits. Mandatory as-of avoidance changes the ordinary
pass; optional repair is checked against that completed first pass.
Exact-head CI and the review-containing main three-OS release remain open.

Final guard audit also requires unchanged content under a retained text ID and
the same known annotation ladder with a valid, non-later selected rung.
The coordinator's19 focused controls pass, including same-ID member/relation
label and note substitutions. Combined guard/causality/stroke/HALCYON-tail
controls pass39tests. Guard head05c69051a's official
[artifact12087829631](https://github.com/tya5/chrona/actions/runs/38998671762/artifacts/12087829631)
is byte-identical on all109paths to the inspected evidence above.

CI38998671762's39 failing cases are accounted for:12 obsolete reservation test
hooks,2 progress-name assertions,13 restored-lane/repair fact projections,
3 packaged comparison mirrors,3 provenance-only Scene hashes,1 civil/working
sign fixture,2 incidental suppression fixtures,2 ownership checks and1 completion
wiring check. Tests now exercise the approved rule, retain exact SVG hashes and
actual geometry assertions, and use deterministic synthetic suppression input.
The private annotation owner completes each option against its own index;
the392-line composer emits only the selected batch and one final completion.
No threshold relaxation, example tuning or old compatibility hook is added.
Fresh exact-head CI and unchanged snapshot identity remain required before merge.
