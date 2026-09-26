# Architecture Review — Approved Visual Target Publication (#462)

**Reviewed design:** [issue-462 design](../../design/issue-462-design-target-publication-design-2026-09-26.md).
**Published base:** `d56eed4bb0d51585622a9d5fff472d57bffd80a5`.

The placement respects the repository's ownership split. Research drawings
are neither executable View resources nor generated corpus artifacts, so
`docs/research/presentation` is their owner. The #441 example-reachability
invariant is preserved, and no package data or schema inventory entry is
needed. The source-to-PNG/SVG relation remains inspectable in one directory.

Against adjacent work, #453 can measure current Scene/SVG against the
published B target without implying equality or treating a hand-drawn mock
as current output. PR #461's fourteen HTML/PNG targets stay documentation
only; no Theme/Layout/Scene policy is inferred from them. The gallery reuse
and materializer specifications remain untouched. No normative behavior,
ownership or public schema changes, hence no ADR/specification change is
required.

Decision: accepted for implementation planning. The remaining operational
risks are PR #461 becoming stale before merge, branch blob availability, and
link update before publication. Each has a direct gate in the implementation
plan. No product-code design gap remains.
