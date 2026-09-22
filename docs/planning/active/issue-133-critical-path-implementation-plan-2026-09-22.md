# Issue 133 Critical-path Implementation Plan

## Preconditions

Implement the merged Issue #133 design only. Deadline does not enter latest-placement analysis; no author-supplied critical tag or renderer calculation is permitted.

## Slices

1. **Scheduler analysis and public port.** Add typed `ScheduleAnalysis` to result/outcome, component-target and backward-pass helpers, calendar-aware float counting, and no-partial-analysis invariants. Test canonical paths, work calendars, fixed points/spans, bounds, rollups, singleton components, and invalid/cyclic graphs.
2. **Projection facts.** Thread current and Snapshot analyses through the use case into typed review items. Add critical role facts and `totalFloat` table-value support, with Snapshot-isolation tests.
3. **Critical relation surface.** Extend View schema/normalization, registry/Theme validation, relation filtering, Scene semantic selection, and fixtures together. Test route provenance and materializer bytes.
4. **Release gate.** Run focused suites, full pytest, public materializers, generated SVG diff review, and an architecture review that searches for graph analysis outside scheduler.

## Publication boundaries

Each slice is its own PR and merge. Before the next slice, verify remote `main`, macOS/Ubuntu CI, merge state, and updated base. Do not start #134 until all slices are merged and Issue #133 is closed.
