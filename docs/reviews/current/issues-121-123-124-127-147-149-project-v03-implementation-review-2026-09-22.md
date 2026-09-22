# Project v0.3 Implementation Review

**Implements:** P3 in
`docs/planning/active/issues-121-123-124-127-147-149-implementation-plan-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-design-review-2026-09-22.md`

## Delivered contract

`timeline/project-v0.3` replaces the Date-only v0.1 Project contract.  It
adds the single `parent` containment edge, unique optional `wbsCode`, optional
`plannedProgress`, exact `{mode: rollup}` schedules, and the closed
`dependency` relation type.  The v0.1 schema and every current v0.1 Project,
profile requirement, fixture, example, contract registry entry, and wheel
resource reference are removed or migrated in this atomic change.  The schema
inventory records v0.3 as the one live Project schema.

## Architecture and responsibility review

Project Core normalizes authored root/sibling order into immutable hierarchy
entries and derives missing display WBS codes.  Core validation owns parent,
cycle, duplicate-code, empty-rollup, and malformed-rollup diagnostics.  The
reference scheduler consumes those Core hierarchy facts to derive a completed
rollup envelope after child placements; it does not infer child dates.  A
rollup remains an ordinary dependency endpoint with derived `start`/`end`.

No View, Layout, Scene, or renderer changed.  Thus P3 adds semantic Project
authority without prematurely selecting WBS rows, table columns, indentation,
or geometry; those responsibilities remain P4.  The typed closure boundary
continues to validate the one current Project schema and exposes the same named
`ProjectContract.scheduler_input` seam.  No compatibility parser or v0.1
fallback remains.

## Acceptance evidence

- Focused hierarchy/scheduler/example/closure tests: 35 passed.
- Full suite: 284 passed, 8 skipped.
- Conformance and schema inventory: passed.
- Module reachability and import-direction checks: passed (50 reachable
  modules; 8 packages, 21 inward edges).
- Five public materializer byte checks: passed; no generated SVG changed.
- Build, installed-wheel smoke, and packaged-schema resource check: passed.

The implementation satisfies P3 and supplies the Project vocabulary required
for P4.  #124 remains open until P7's zero-transition inventory gate; #147
remains open until P4.5's final presentation-vocabulary closure.
