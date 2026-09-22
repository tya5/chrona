# Issue 99 Step 4 — Schema/Contract Correction Implementation Plan

**Status:** Approved implementation plan.  **Design authority:**
`issue-99-schema-contract-correction-2026-09-22.md`, merged by PR #118.

## Scope

Correct only the `chrona/view/v0.1` `visibility.relations` schema drift that
blocks exact-schema contract construction for the public aster-ssd materializer.

## Steps

1. Extend the v0.1 schema relation visibility union with the already-supported
   `{mode, overflow}` object form.  Keep the legacy enum and constrain the
   object values exactly as recorded in the correction design.
2. Add an acceptance test which validates every public v0.1 View with the
   schema and the local presentation-resource schema registry.
3. Run the v0.1-focused schema test, full pytest, conformance, import and
   reachability checks, and all declared public materializers.  Reject any SVG
   diff; do not edit generated artifacts.

## Acceptance criteria

- aster-ssd's declared View validates under its declared v0.1 schema.
- Invalid relation overflow or an unsupported object mode is rejected.
- All public v0.1 Views validate, all materializers retain byte identity, and
  no runtime parser accepts a syntax absent from its exact schema.

## Publication boundary

The schema correction and evidence are one PR.  Only after it merges may the
preserved C99-4A contract implementation be restored and rebased.
