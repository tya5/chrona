# Issue 99 Step 4 / C99-4B — Optional Review Contract Implementation Plan

**Status:** Approved implementation plan.  **Design authority:**
`issue-99-typed-contracts-c99-4b-design-2026-09-22.md`, merged by PR #130.

## Scope

Replace every opaque optional closure resource with an exact-schema frozen
contract, then change projection/content consumers to accept those named
contracts.  Preserve rendered output and optional-input diagnostics.

## Steps

1. Extend the local schema registry with revision-store reference, actual-set,
   snapshot-ref, profile-package, summary-profile, and detail-profile schemas.
   Add named contract types and remove `OpaqueResourceContract` and its
   fallback branch.
2. Add typed `RenderClosure` accessors for actual, snapshot project, profile
   packages, summary profile, and detail profile.  Retain absence as `None`,
   not an empty synthetic document.
3. Change `build_review_projection` and `normalize_v05_surface_content` to
   accept the relevant contract types.  The render use case passes contracts,
   while those domain owners access their named frozen facts/body fields.
4. Add exact-schema, optional-absence, snapshot-identity, and no-opaque
   structural tests.  Keep the closure input-read evidence working.
5. Run focused tests, full pytest, conformance, import/reachability checks,
   all five materializers, and a generated SVG diff.  Do not regenerate or
   modify artifacts.

## Acceptance criteria

- No `OpaqueResourceContract`, unknown-version parser fallback, or generic
  optional closure mapping remains.
- Every resource loaded by `resolve_render_context` has an exact schema entry.
- Projection and v0.5 content normalization signatures use contracts for
  closure resources.
- Optional absence and all existing stable diagnostics/bytes are unchanged.
- Full verification succeeds without generated SVG changes.

## Publication boundary

C99-4B implementation is one PR after this plan merges.  C99-4C begins only
after that implementation merge.
