# View Selection Capability Closure — Implementation Amendment

**Amends:**
`issues-121-123-124-127-147-149-wbs-view-selection-implementation-amendment-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-view-selection-capability-design-correction-2026-09-22.md`

## P4 refinement

The v0.3 schema removes `selection.include.entityIds` and `profiles`.  Migrate
every current View to the closed `ids`/`types` predicate; do not retain a
runtime branch for the removed fields.  Add negative schema fixtures proving
the removed keys reject, and projection fixtures proving the remaining
intersection predicate both selects flat rows and supplies hierarchy expansion
roots.

Before P4's schema migration, restore the isolated projection draft only after
this amendment merges, revise it to consume those closed predicates, and run
the hierarchy fixture set.  No raw Project field is guessed as an entity edge,
and no profile resolver is added to View.

## Acceptance addition

P4 acceptance requires a one-way proof: every View v0.3 selection key has a
defined typed input and deterministic projection behavior; no ignored,
syntactic-only selection key survives in schema, closure record, or runtime.
