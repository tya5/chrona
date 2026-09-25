# Implementation-Plan Amendment — Presentation Diagnostic Aggregation (#450)

**Amends:** `issue-450-presentation-diagnostic-aggregation-implementation-plan-2026-09-26.md`

## Reason for the split

The original I450-3 combined three ingress topologies: explicit Draft files,
preset/guided authoring, and immutable Context resolution.  They share the
published collector and rejection contract, but their complete declared
resource sets become known at different boundaries.  In particular, a preset
or Context may name further resources only after its own envelope is valid;
an unreadable or invalid envelope remains a terminal boundary error by the
accepted design.  Splitting publication avoids manufacturing a partial
resource set while preserving the single collector and aggregate transport
architecture.

## Replacement slices

### I450-3a — Explicit Draft transport

Replace sequential explicit Draft resource parsing with collection over the
already declared CLI file paths (Project, View, Theme, Color Scheme, Layout,
and optional inputs/catalogs).  Reject a multiple-finding result through the
existing CLI `diagnostics` array with resource provenance.  Preserve the exact
legacy single-finding `ClosureError`/CLI result, including union explanation.

### I450-3b — Declared indirect ingress transport

Apply the same collector after a schema-accepted preset, guided workspace, or
immutable Context establishes its resource declarations.  Continue to treat
unreadable content, identity failures, or invalid declaration envelopes as
terminal boundary diagnostics; do not infer a resource set.  Validate every
known independent resource before closure-only checks.

I450-4 begins only after both replacement slices are published and reviewed.

## Acceptance additions

- The historical one-error Draft union fixture remains byte-compatible.
- The literal #450 View/Theme three-error Draft fixture serializes all three
  findings in stable declaration/pointer order, each with resource provenance.
- I450-3b adds equivalent collector tests for the known resource sets of
  guided/preset and immutable Context ingress.
