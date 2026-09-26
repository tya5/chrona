# Design Plan — Missing Actual Due-State Semantics (#476)

## Published baseline

At public `main` `fbe0130e`, #476 is open with no comments. #470's merged
presets deliberately omit `missingActual` because future work is currently
marked missing. Specification 06's comparison truth table and Specification
39 define missing Actual by absent observation alone. Current View projection,
table cells, summary count, Layout track allocation and mark placement each
reconstruct that fact; the as-of date is not carried on `ReviewItem`. The
published `actual.yaml` for HALCYON-1 fixes as-of 2027-08-20. This is a
semantic change, not a palette or geometry tweak. #466's untracked local
schema draft is unrelated and must be preserved.

## Literal issue acceptance criteria

1. On HALCYON-1 at as-of 2027-08-20, items planned to finish after
   2027-08-20 carry no missing-actual mark.
2. Items due on or before as-of with no observation still carry it. `tvac`
   (planned finish 08-20, no observation) is the boundary case, and a test
   covers it.
3. The `missingActual` table cell follows the same rule.

## Use cases and design questions

1. Specify one View-owned due-state predicate for a selected planned span
   (exclusive finish) and point at the explicit Actual as-of; define what
   happens when no Actual set/as-of exists, and ensure an incomplete but
   present observation is never labeled absent.
2. Decide whether `missingActual` is a due-and-absent boolean or tri-state
   availability. The table's `whenTrue`/`whenFalse` presentation must not
   misleadingly call a future item “Recorded”. Review summary counts too.
3. Give the same normalized fact to semantic roles, table cells, summary,
   Layout track reservation and mark placement. No independent date checks in
   Scene or adapters. Check explicit/shared rows, snapshot/scenario members,
   milestone points and a missing or optional Actual input.
4. Review Specifications 06, 08, 25, 39 and 46, #49's typed presentation
   contract, and the View→Layout→Scene boundary. Update living specifications
   and record intended migration of existing generated output.
5. Define boundary tests for `finish == asOf`, `finish > asOf`, point `at ==`
   / `> asOf`, observation present but incomplete, table semantics and
   HALCYON end-to-end SVG/Scene. Inventory affected public materializers and
   exact regenerated evidence before code.

## Ordered design and publication slices

Publish this plan first. Then publish a selected semantic contract, living
specification changes and whole-architecture review. Publish an implementation
plan naming each code owner, tests, materializer changes and acceptance gate
before product edits. Implement, run focused tests and one public materializer
batch, inspect full CI, publish a literal acceptance review, and close #476
only when all three rows have direct public evidence.

## Unverified at plan publication

The exact public SVG/Scene set whose bytes change, whether any example exposes
the `missingActual` table column, and the correct table presentation for a
not-yet-due item remain design questions. They are not presumed complete by
the existing green #470 CI.
