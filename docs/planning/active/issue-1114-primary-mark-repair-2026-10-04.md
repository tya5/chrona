# Issue #1114: primary-mark-safe route completion

Public baseline: `cc6baa90`; safety-only PR #1138 (`2609e72e`) is not accepted.
Owner retained compliant-route preservation. Current evidence and the published
[design plan](https://github.com/tya5/chrona/issues/1114#issuecomment-5976935111)
are consolidated in the [status](https://github.com/tya5/chrona/issues/1114#issuecomment-5977055640).

## Design plan and selected correction

The visibility-grid body search already respects mark obstacles. The reversal
repair subsequently exempts endpoint hosts from its new jog segments, selects
the first jog, and only then encounters the primary-mark safety guard. It can
discard a pair although a later existing jog is safe. A neutral witness uses
target rectangle `(0,90,10,100)` and points
`((20,110),(0,110),(0,90),(0,95))`: the first jog at x=8 crosses 10 units of the
host interior; the next existing jog at x=12 is clear. The authorized terminal
corridor lies on the target boundary. No corpus coordinates enter runtime.

Apply primary-mark validation while enumerating replacement jogs, before
committing the first repair. Validate the two new segments, not an incomplete
whole path that may still contain another reversal. Keep the final completed
path guard. Preserve existing jog order, body search, quality budgets, port
order and comparison-host authorization; do not introduce a joint solver.
An already compliant first repair remains identical. Back-route and rounded
corner completion already have primary-mark guards; this slice does not add
new back-route templates, node-aware ordering or S-jog policies (#1109).

Architecture review: Specifications 33/50 assign search and completed geometry
to Layout. The existing primary-mark contract applies to repair candidates
as well as final paths; this closes an implementation gap without changing
that contract. Scene observes completed paths; adapters serialize. No new
schema, diagnostics, resource migration, threshold or compatibility mode.

## Implementation plan and gates

1. Publish this correction/review/plan before product changes.
2. Add an optional replacement-segment validator to `repair_self_reversal`
   in `layout/routing.py`; wire the existing primary-mark validator from lane
   selection and non-lane completion in `layout/surface_routes.py`. Add neutral
   unsafe-first/safe-later and compliant-first preservation tests in
   `tests/unit/chrona/presentation/layout/test_routing_placement.py`.
3. Run focused routing/ports/Scene tests. CI owns one complete public
   Scene/SVG snapshot; compare every previously compliant route and visible
   name, not merely counts. A remaining preservation failure returns to design,
   not resource edits, suppression waivers or weakened tests.
4. Accept only after literal acceptance and exact-main release evidence.

| Literal acceptance | Required evidence |
| --- | --- |
| start-to-at, and start-to-start, with the target to the right; | Neutral fixtures. |
| the mirrored end-to-end case with the target to the left; | Neutral fixture. |
| a bar with no free gap above, and one with no free gap below. | Neutral fixtures. |
| For each, no relation segment overlaps the interior of any bar by more than the stroke width, and the first segment leaves the port outward. | Completed geometry and Scene checks. |
| A Scene check counts own- and foreign-bar crossings corpus-wide; it must be 0 after regeneration. | CI snapshot, all public Scenes. |
| Existing compliant routes are unchanged. | Exact before/after route points; still unverified. |
| On target B, `avionics-cdr` no longer crosses the Avionics bar. | Actual Scene and SVG. |

## Current verification

The replacement-segment correction is implemented; 59 focused routing,
ports, back-route and Scene safety tests pass, including the neutral witness
and exact preservation of a compliant first repair. A fresh public
`gallery-editorial-lanes` materialization in a temporary directory still has
zero crossings but loses detector-tvac/shipment-campaign, changes six compliant
routes and changes member names. Therefore the issue is **not accepted**:
the narrow repair gap is fixed, but the coupled corridor/name plan still needs
design correction. The committed old Editorial fixture is not evidence for
this new render. No generated repository files were changed.
