# Issue 254 Advanced-Contract Example Selection Implementation Amendment

**Amends:**
`docs/planning/active/issue-254-advanced-contract-example-implementation-plan-2026-09-22.md`

**Design authority:**
`docs/reviews/current/issue-254-advanced-contract-example-selection-design-correction-2026-09-22.md`

E254-1 additionally replaces `halcyon-02-programme-board`'s type-only
selection with the exact current object IDs plus its existing type guard. The
implementation records the five pre-existing generated SVG hashes before and
after materialization, and fails acceptance on any difference. This preserves
the existing View's presentation while excluding only the new rollup from its
previously implicit universe.
