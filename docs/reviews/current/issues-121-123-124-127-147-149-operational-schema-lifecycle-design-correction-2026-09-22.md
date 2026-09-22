# Operational Schema Lifecycle — Design Correction

**Amends:**
`issues-121-123-124-127-147-149-schema-inventory-transition-design-correction-2026-09-22.md`

## Evidence

Specification 35 defines `chrona/actual-intake-batch/v0.2` as the immutable
operational resource.  The v0.2 schema has the common resource envelope and
the M26 command path dereferences `kind: actual-intake-batch` then consumes its
`body`.  In contrast, `operational.resources._schema_store` and several legacy
fixtures still name the flat v0.1 schema.  That is an incomplete migration, not
two supported operational contracts.

## Decision

`actual-intake-batch/v0.2` is the one **live** contract.  v0.1 is
**transitioning** only until P1 and has no authoring, CLI, or scaffold route.
P1 atomically changes the operational schema registry, fixtures, tests,
examples, package-resource list, and documentation references to v0.2, then
deletes v0.1.  Its removal slice is P1 rather than P4 because it is owned by
the M26 operational boundary, not the presentation closure.

The batch's body remains an immutable observed-input document.  The Command
Engine may translate that validated body into an ActualSet update, but it must
not accept a bare v0.1 document, infer a batch identity, or make a second
schema decision.  Core, View, Layout, Scene, and renderers remain unaffected.

## Acceptance

Tests prove that v0.2 validates and reaches `applyActualIntakeBatch`, v0.1 is
not packaged or accepted, all public operational examples use v0.2, and the
schema inventory lists exactly one live actual-intake-batch kind.  This joins
the P1 inventory/reachability and full inherited-suite gate.
