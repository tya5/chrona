# Schema Inventory Transition — Design Correction

**Amends:**
`issues-121-123-124-127-147-149-design-review-2026-09-22.md`

## Trigger

P1 implementation discovery established that the current closure still accepts
multiple versions not only for Project, but also for View and ActualSet.  A
binary `live`/`removed` inventory would therefore either falsely advertise
multiple contracts as current or omit schemas still required by a materializable
closure.  That violates the inventory's purpose and the program's no-hidden-
migration rule.

## Corrected lifecycle model

The checked-in schema inventory has exactly three explicit states:

| State | Meaning | README treatment | Allowed consumer |
| --- | --- | --- | --- |
| `live` | The sole authorable current contract for a kind. | Listed in the primary index. | Current product/conformance/tooling paths. |
| `transitioning` | A temporary accepted predecessor with a named removal slice and successor. | Listed in a separate migration table, never as authorable current syntax. | Only the explicitly named migration consumers. |
| `retired` | Not packaged or present under `schemas/`. | Not listed as a schema; recorded only in release notes/review. | None. |

Each transitioning entry must name its successor, removal slice, and a test that
proves no ordinary authoring path selects it.  It is forbidden for a new feature
or scaffold to create one.  P3 removes the Project v0.1 transition; P4 removes
the View and ActualSet transitions where their successor designs are complete;
P6 removes the Render Context v0.7 transition; P7 rejects any remaining
transitioning entry.  Deferred M10/staged schemas have no successor in this
program and are retired in P1, not marked transitioning.

The inventory remains bidirectional: every packaged schema is one declared
state, and every state has declared approved consumers.  The generated README
is still exact, now explicitly distinguishing one live contract per kind from
temporary migration readers.  This correction changes inventory presentation
only; it adds no compatibility parser and does not extend acceptance beyond the
versions already reachable before the program.

## Architecture review

The correction preserves schema-first ownership and clean final state while
making migration truth reviewable.  It prevents CLI/init from selecting a
predecessor, avoids a premature deletion that breaks immutable closure
reproduction, and gives P7 a mechanically checkable zero-transition gate.  No
Core, View, Layout, Scene, renderer, or Store responsibility changes.
