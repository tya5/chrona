# Issue #308 Progress Fill Accessibility Design Correction

**Status:** Accepted correction  
**Date:** 2026-09-23  
**Corrects:** [Specification 61](../../specification/61-progress-fill-marks.md)

## Finding

The original wording said that a progress-fill primitive would carry an
accessible description containing its declared source and percentage.  The
implemented and existing Scene contract carries a primitive source reference
and semantic purpose, but deliberately has no per-primitive accessible-text or
arbitrary metadata payload.  Adding such payload solely in a renderer adapter
would create a second, adapter-specific semantic contract.

## Decision

Keep #308 within the established Layout → Scene → adapter boundary.  The
completed placement projects as `progressFill`, with its host object source
reference and stable semantic purpose.  This makes its declared meaning
machine-identifiable independently of colour.  The numeric fraction remains
authoritative in Project or Actual data; consumers combine it with that source
reference when needed.

Accessible percentage prose is deferred until a versioned Scene metadata
contract can define ownership, serialization, and all-adapter behavior.  It is
not introduced as a target-local exception.

## Architecture review

This correction preserves the repository's renderer-neutral placement model:
Layout owns geometry, Scene owns semantic projection, and adapters only emit
completed primitives.  It avoids coupling the progress feature to SVG-specific
ARIA text and does not alter scheduling, materialization identity, colour
scales, or inside-label policy.  The correction is therefore compatible with
Specifications 08, 50, and 60 and requires no implementation change.
