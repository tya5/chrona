# Operational Schema Lifecycle — Implementation Plan Amendment

**Design authority:**
`docs/reviews/current/issues-121-123-124-127-147-149-operational-schema-lifecycle-design-correction-2026-09-22.md`

P1 includes one atomic M26 sub-slice before inventory publication:

1. make `actual-intake-batch-v0.2.schema.yaml` the only registry and packaged
   schema for the batch kind;
2. migrate operational unit/integration fixtures, examples, documentation, and
   package-resource assertions to its envelope/body shape;
3. delete the flat v0.1 schema and every v0.1-only fixture; and
4. add positive v0.2 and negative retired-v0.1 acceptance tests.

The sub-slice is accepted only if `applyActualIntakeBatch` resolves a v0.2
reference through the same immutable reader path as production, the complete
M26 suite remains green, and no schema/resource path names v0.1.  It publishes
with the P1 inventory checker rather than as a separate compatibility phase.
