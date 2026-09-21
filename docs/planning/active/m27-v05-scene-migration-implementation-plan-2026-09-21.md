# M27 v0.5 Scene Migration Implementation Plan — 2026-09-21

**Status:** Authorized by `m27-v05-scene-migration-design-review-2026-09-21.md`.

| Slice | Scope | Completion evidence |
|---|---|---|
| I27-R1 | `ThemeTokenView`, v0.5 Scene builder input seam including immutable `MeasuredSources`, and missing token/input diagnostics | typed token/measurement tests; no legacy settings/paint shape import; full regression |
| I27-R2 | Core SceneSurface: slots/rows/groups, measured typography/table cells, calendar axis, plan/Actual/milestone/variance/missing-Actual primitives | A27-02–A27-04; overflow and provenance tests |
| I27-R3A | v0.5 SVG token adapter and current Theme role closure | adapter has no raw-resource reads; full regression |
| I27-R3B1 | Optional content normalization, group decoration, legend/notes, and finite dependency routes | full regression and conformance |
| I27-R3B2 | Remaining optional families: detail/summary, annotations, and markers | A27-01/A27-05/A27-06 |
| I27-R4 | Public CLI switch and removal of reduced-path reachability | A27-08; Context/Color Scheme/Layout integration tests |
| I27-R5 | Generic materializer, example reproduction, conformance, final review and issue closure | A27-07/A27-09/A27-10; full suite and conformance |
| I27-R6 | Rich primitive acceptance: role typography, bounded annotation leaders, and dependency markers | A27-01/A27-05; reopen #29/#33 only after evidence |

I27-R1 was reopened by `m27-scene-input-measurement-design-amendment-2026-09-21.md`;
its prior publication established the token API but did not yet close the measurement
input boundary. Every slice begins with executable evidence, consumes only the Specification 37
closure, passes the full inherited regression suite, receives a slice review, and is
published to `main` before the next slice. A need for another token property, new
resource input, or renderer policy reopens Specification 37 before code changes.

I27-R2 uses the ISO axis fit rule approved in
`m27-axis-policy-design-amendment-2026-09-21.md`; it does not add an axis resource or
fall back to a fixed cadence.

## I27-R6 execution plan

1. Extend the current Theme v0.2 schema/token view and `TextLayout` with declared
   role typography; add roles/tokens to both materialized Themes without changing the
   Context resource boundary.
2. Complete the Scene builder's role selection, marker carry-through, and object-mark
   annotation resolution/placement/leader construction using only projection,
   measured input, and Layout Manifest evidence.
3. Complete SVG serialization for resolved text size and referenced marker
   definitions/endpoints; keep raw authoring resources unreachable from the adapter.
4. Add focused diagnostics and provenance/bounds tests, then regenerate materialized
   examples through the public CLI.
5. Run full regression, conformance, and materializer checks; publish the slice
   review and only then close the remaining rich-primitive issues.
