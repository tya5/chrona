# Design Correction: Optional Source Participation in Layout (#350)

**Status:** Design complete — required for byte-stable absent annotation rails.

## Finding

An optional Layout slot was schema-valid when its source was unavailable, but
the render use case still supplied a placeholder measurement. The engine then
arranged the optional root-level annotation rail even when the View selected no
annotations. This changed the primary review extent and generated SVG bytes.
That behavior contradicts both optional-source semantics and the annotation
rail correction.

## Corrected contract

Source construction omits an optional source when its selected semantic content
is absent. Layout participation is determined from the measured-source map:
an optional slot with no measurement is inactive and contributes neither
intrinsic size, gap, nor an arrangement decision. Required slots remain
strictly diagnosed when their measurement is unavailable.

This is an engine rule, not an annotation-specific exception. It applies
consistently to linear, flow, grid, and overlay traversal while retaining each
active child’s declared profile path for diagnostics and token resolution.

## Architecture consistency review

View continues to decide semantic presence; the render use case declares only
the selected source facts; Layout decides whether an optional layout node
participates and computes all resulting geometry. Scene receives no absent
slot or placeholder geometry. This restores stable public materialization
without adding compatibility rendering paths or adapter policy.

## Implementation and acceptance plan

1. Omit no-content optional source inputs and skip their slot measurements.
2. Make Layout engine traversal ignore only optional slots lacking a
   measurement, preserving original profile indices for active siblings.
3. Add source/engine tests for inactive optional slots and the annotation
   visual integration fixture.
4. Verify all public materializers are byte-identical when annotations are
   absent; then run focused and full suites.
