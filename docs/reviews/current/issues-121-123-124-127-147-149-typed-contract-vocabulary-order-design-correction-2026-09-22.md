# Typed Contract Vocabulary Order — Design Correction

**Amends:**
`issues-121-123-124-127-147-149-design-review-2026-09-22.md`

## Trigger

The completed #147 foundation establishes schema-first immutable resource
contracts and removes generic closure-document escape hatches.  Its completion
audit found that `TableColumn`, `LegendEntry`, and `SummaryPanel` cannot be
truthfully frozen as final field records before P3/P4: Project v0.3 changes
hierarchy truth and P4 changes the View table-column and subtree-summary
vocabulary.  Freezing current v0.2 shapes first would create a deliberately
short-lived second parser and record migration.

## Corrected delivery order

1. Keep the completed #147 closure boundary as the sole resource parsing seam.
2. Deliver P3 Project v0.3 and P4 View/WBS vocabulary through that seam.
3. Immediately deliver **P4.5 — typed presentation vocabulary closure**:
   `TableColumn`, `LegendEntry`, `SummaryPanel`, row/group/visibility records,
   and field-level schema-to-record completeness fixtures.  It removes the
   remaining contract-owned adapter mappings wherever the schema is closed;
   only schema-declared open extension payloads remain frozen mappings.
4. Close #147 only after P4.5, not after the Context foundation.

This is a sequencing correction, not a compatibility layer.  It preserves one
parser and one final vocabulary while allowing P3/P4 to consume typed resource
contracts through their existing explicit adapter inputs.

## Architecture review

Project remains semantic authority, View owns selection and row policy, Layout
owns geometry, Scene projection, and renderers serialization.  P4.5 is a
closure-boundary representation change only: it cannot alter scheduling, WBS
meaning, placement, or output policy.  Its tests must prove that no closed
schema field is omitted from a named record and that no raw YAML mapping reaches
the render use case, projection, content, Layout, Scene, or renderer.
