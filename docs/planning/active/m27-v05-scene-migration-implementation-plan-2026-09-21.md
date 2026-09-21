# M27 v0.5 Scene Migration Implementation Plan — 2026-09-21

**Status:** Authorized by `m27-v05-scene-migration-design-review-2026-09-21.md`.

| Slice | Scope | Completion evidence |
|---|---|---|
| I27-R1 | `ThemeTokenView`, v0.5 Scene builder input seam including immutable `MeasuredSources`, and missing token/input diagnostics | typed token/measurement tests; no legacy settings/paint shape import; full regression |
| I27-R2 | Core SceneSurface: slots/rows/groups, measured typography/table cells, calendar axis, plan/Actual/milestone/variance/missing-Actual primitives | A27-02–A27-04; overflow and provenance tests |
| I27-R3 | Optional Scene families and v0.5 SVG token adapter: group decoration, legend, detail/summary, annotations, finite routes/markers | A27-01/A27-05/A27-06; adapter has no raw-resource reads |
| I27-R4 | Public CLI switch and removal of reduced-path reachability | A27-08; Context/Color Scheme/Layout integration tests |
| I27-R5 | Generic materializer, example reproduction, conformance, final review and issue closure | A27-07/A27-09/A27-10; full suite and conformance |

I27-R1 was reopened by `m27-scene-input-measurement-design-amendment-2026-09-21.md`;
its prior publication established the token API but did not yet close the measurement
input boundary. Every slice begins with executable evidence, consumes only the Specification 37
closure, passes the full inherited regression suite, receives a slice review, and is
published to `main` before the next slice. A need for another token property, new
resource input, or renderer policy reopens Specification 37 before code changes.

I27-R2 uses the ISO axis fit rule approved in
`m27-axis-policy-design-amendment-2026-09-21.md`; it does not add an axis resource or
fall back to a fixed cadence.
