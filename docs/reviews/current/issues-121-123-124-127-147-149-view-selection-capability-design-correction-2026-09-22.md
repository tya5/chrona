# View Selection Capability Closure — Design Correction

**Amends:**
`issues-121-123-124-127-147-149-wbs-view-selection-design-correction-2026-09-22.md`

## Trigger

The v0.1/v0.2 View schema admits `selection.include.entityIds` and `profiles`,
but Project does not define an entity edge for arbitrary object fields and the
View projection has no profile-resolution input.  Their acceptance would be
syntactic only: each would require an undocumented interpretation in View.

## Decision

View v0.3 has a closed selection predicate containing only `ids` and `types`.
Both are directly defined by the Project/placement boundary.  `entityIds` and
`profiles` are removed rather than retained as ignored or compatibility fields.
An entity- or profile-aware selection capability requires a future owner to
define the Project edge, resolution input, predicate algebra, diagnostics, and
selection tests before it is introduced.

In hierarchy mode, these two predicates select expansion roots under the
previous correction's rules.  With neither predicate, Project roots are the
implicit expansion roots.  Outside hierarchy mode, they select ordinary rows
by intersection as before.

## Architecture review

This keeps View selection declarative and verifiable from its typed Project and
placement inputs.  It does not move extension/profile resolution into View,
guess an entity-bearing field, or add a raw-mapping escape hatch.  Project Core,
Layout, Scene, and renderer responsibilities are unchanged.
