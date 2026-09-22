# Issue 94 P94-3 — Staged Module Deletion Implementation Plan

**Status:** Approved implementation plan.  **Design authority:**
`issue-94-completion-design-plan-2026-09-22.md`, merged at `a64f704`.

## Scope

Delete the 19 modules listed in D94-1, every test whose only purpose is to
exercise them, and their 19 entries in `tools/staged_modules.txt`.  Retain the
reachability lint and CI invocation; its successful state after this change is
zero staged modules and no orphans.

## Steps

1. Map each module to its dedicated test file and verify that no reachable
   product module imports it.  Do not alter the CLI, schema, materializer, or
   public examples.
2. Delete each module/test pair atomically.  Delete integration tests only when
   their imported API is solely one of the removed modules; preserve tests for
   reachable paths.
3. Empty the staged list while retaining its ownership contract comments, now
   stating that a future staged entry needs a concrete owning issue and expiry.
4. Run focused collection/import checks, the reachability lint, full pytest,
   five materializer byte checks, and a generated-SVG diff.  The suite count is
   expected to decrease only by the removed dedicated tests; no generated SVG
   may change.

## Acceptance criteria

- No P94-3 module or test remains in the repository.
- `tools/check_module_reachability.py` reports zero staged modules and no
  orphaned source module.
- There is no import from a product entry point to a deleted module.
- Full test suite and both CI platforms pass; all five public materializers
  reproduce their checked artifacts without a generated SVG diff.
- The resulting PR contains no compatibility shim or undocumented product
  command.

## Publication boundary

The deletion and its evidence are one implementation PR.  P94-4 begins only
after this PR is merged into `main`.
