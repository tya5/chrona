# WBS View Selection and Summary — Implementation Amendment

**Amends:**
`issues-121-123-124-127-147-149-implementation-plan-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-wbs-view-selection-design-correction-2026-09-22.md`

## P4 refinement

Before creating View v0.3, add focused Project-to-View fixtures for predicate
roots, inclusive depth expansion, overlapping root de-duplication, selected
non-root subtrees, and sibling ordering.  The projection implementation must
consume Project Core normalized hierarchy facts; it must not traverse raw
parent mappings as a second semantic authority.

The View schema and projection then add explicit-row `depth` and `parentRow`
validation, `wbsCode` and title breadcrumb `path` table sources, and
`scope: subtree` summary selection.  Test invalid asserted edges, unselected
summary roots, non-hierarchy scope, and comparison-track de-duplication.

Only after semantic fixtures are green, migrate View v0.1/v0.2 resources to
one v0.3 contract, introduce the theme indent token and summary-bar semantic,
and connect their completed Layout placements to Scene projection.  The
connection test must prove Scene receives neither a tree nor raw View policy;
it emits only Layout's completed text and summary-bar placements.

## P4 acceptance additions

P4 is accepted only if hierarchy root/expansion behavior, explicit-row edges,
WBS code/path values, and subtree membership have direct deterministic tests,
in addition to the original measured-layout, SVG/accessibility, materializer,
full-suite, and two-platform gates.  P4.5 follows unchanged and freezes the
finalized vocabulary as named closure records.
