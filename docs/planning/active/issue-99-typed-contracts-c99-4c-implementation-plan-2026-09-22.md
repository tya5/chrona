# Issue 99 Step 4 / C99-4C — Closure Consumer Completion Implementation Plan

**Status:** Approved implementation plan.  **Design authority:**
`issue-99-typed-contracts-c99-4c-design-2026-09-22.md`, merged by PR #137.

## Scope

Remove generic closure kind lookup from product consumers and make the
typed-closure boundary structurally enforceable without changing SVG output or
known-unused input policy.

## Steps

1. Replace `_Closure` with a typed `ClosureReadLedger`: named methods record
   reads for required resources, actual, snapshot, detail, and packages;
   summary remains unmarked unless actually consumed.
2. Remove public `RenderClosure.resource(kind)` access from consumers.  Keep
   any identity iteration needed by closure resolution private to that module.
3. Change projection and content-normalization public signatures to named
   contracts and unwrap their frozen domain data at the function boundary.
   Update direct tests to construct contracts rather than pass resource YAML.
4. Add AST/source tests forbidding generic closure lookup and generic resource
   mapping parameters at these public boundaries.  Add typed closure
   projection/read-ledger characterization.
5. Run focused tests, full pytest, conformance, import/reachability checks,
   all public materializers, and a generated SVG diff.  No artifacts change.

## Acceptance criteria

- `render_review.py` has no `_Closure`, kind-string resource retrieval, or
  `ClosureResource` reference.
- Projection/content entry points have contract-typed closure inputs.
- Structural tests reject reintroduction of those generic paths.
- Existing diagnostics, read-input result, and all five public SVG bytes are
  unchanged.

## Publication boundary

This is the final Step 4 implementation PR.  Step 5 planning begins only after
it merges.
