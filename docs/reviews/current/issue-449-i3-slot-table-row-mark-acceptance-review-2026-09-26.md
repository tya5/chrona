# Acceptance Review — Visible Slot, Table, Row, and Mark Fallbacks (#449 I449-3)

**Design:** `issue-449-visible-fit-failure-policy-design-2026-09-25.md`.
**Implementation plan:** `issue-449-visible-fit-failure-implementation-plan-2026-09-25.md`.

## Decision

Accepted.  A requested table/timeline extent is now a minimum Layout
allocation for the I449-3 families, rather than a refusal boundary.  The
completed Layout result retains measured table columns, P1 rows, tracks, and
marks; it expands the completed canvas where that geometry reaches beyond the
requested extent.  Scene projects the canvas and typed warnings unchanged;
the CLI reports those records after the artifact has been written.

## Acceptance evidence

| Requirement | Evidence | Result |
| --- | --- | --- |
| Oversized table content remains visible | `place_table_columns` retains natural widths for `visible-overflow`; a declared ellipsis representation retains its measured minima even when the requested slot is smaller. | Pass |
| P1 rows and marks are not compacted or rejected | `place_rows` distributes surplus only when it exists; otherwise it preserves required extents.  The multi-lane/multi-milestone fixture renders at a fixed 180px request with `W_LAYOUT_ROW_DENSITY` and `W_LAYOUT_MARK_OVERFLOW`. | Pass |
| Completed output is target-neutral | `_completed_canvas` is Layout composition code.  It unions completed geometry before Scene; no Scene or renderer selects an extent. | Pass |
| Every affected completed item has typed evidence | Table columns/text, overflowing rows, and overflowing marks emit ordered `FitWarning` records.  Scene v0.6 serializes them and the CLI emits the same values to stderr. | Pass |
| A public Scene cannot omit its canvas | Scene v0.6 requires `canvasBounds`; serialization rejects an incomplete surface. | Pass |
| Existing explicit degradation stays explicit | The ellipsize allocator tests remain deterministic, and no normal path uses ellipsis, clipping, or suppression. | Pass |

## Generated evidence review

`halcyon-1/replan-baseline` has one pre-existing visible Work package cell
escape.  Its SVG bytes do not change.  Its regenerated Scene adds exactly one
`W_LAYOUT_VISIBLE_OVERFLOW` record for `cell:emc:Work package`, with the
measured `178.275` required inline extent and `172.3077272727273` available
extent.  This is the intended inspection-only evidence addition.

## Verification

- Focused layout, Scene, use-case, CLI, and render tests: 150 passed.
- Scene primitive-delivery structural check: passed.
- Diagnostic inventory: regenerated and passed freshness check.
- Conformance: passed.
- Public materializer suite: 25 passed after the reviewed Scene update.

## Architecture consistency

The change preserves Project/View declaration, Theme measurement, Layout
completion, Scene projection, and renderer serialization boundaries.  It does
not relax invalid metric, malformed layout, or resource failures.  Remaining
label, axis, route, group-header, and network families stay deliberately out
of this slice and are owned by I449-4.
