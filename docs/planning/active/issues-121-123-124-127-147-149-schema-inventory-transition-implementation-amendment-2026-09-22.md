# Schema Inventory Transition — Implementation Plan Amendment

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-schema-inventory-transition-design-correction-2026-09-22.md`

This amendment replaces P1/P7's binary inventory assumption in the main
implementation plan.

## P1 correction

P1 adds the three-state (`live`, `transitioning`, `retired`) manifest and its
bidirectional checker.  It retires deferred/staged schemas with no current
product route, including the M10 DateTime Project v0.2 route.  It registers
each currently accepted predecessor as `transitioning` with its named successor,
removal slice, and allowed migration consumers.  The README separates the
single authorable live index from transition rows.  No init/scaffold/default
may select a transition row.

## P7 correction

P7 fails if any `transitioning` schema remains.  Its final report records the
removed migrations and proves one live version for every kind.  P3, P4, and P6
must each delete their own transition rows as part of their atomic migration;
P7 is the verification and final-retirement gate, not a cleanup opportunity to
hide an incomplete migration.

## Additional acceptance evidence

Focused tests prove that: a live manifest entry has exactly its declared
approved roots; a transition entry has successor/removal metadata; ordinary
authoring routes reject selection of a transition schema; and an unclassified
packaged schema fails CI.  Full inherited conformance, package-resource checks,
and output evidence remain required.
