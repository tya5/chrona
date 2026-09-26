# Implementation Plan — Presentation Error Pointer Transport (#477)

**Predecessors:** [design plan](issue-477-presentation-error-pointer-design-plan-2026-09-26.md), [design](../../design/issue-477-presentation-error-pointer-design-2026-09-26.md), [architecture review](../../reviews/current/issue-477-presentation-error-pointer-architecture-review-2026-09-26.md).

## Literal acceptance gate

1. Every presentation-layer error that carries a resource pointer reaches the
   CLI diagnostic's `sourceRef` with that pointer. `LayoutError`,
   `ThemeTokenError` and `ScenePaintError` are the known cases.
2. A CLI test renders a Theme without `timeline.groupHeader.blockSize` under
   header grouping and asserts
   `sourceRef: /body/metrics/timeline.groupHeader.blockSize`.
3. A CLI test renders a Theme without `roles.numeric` with a `Δ` column and
   asserts the role pointer.

## P1 — Single transport slice

Owners: `src/chrona/usecases/render_review.py` converts precisely the three
typed exceptions at its public boundary; the existing solver-local conversion
is removed if it becomes redundant. `src/chrona/app/cli.py` should not need a
new detector-specific branch. `tests/cli/test_cli.py` exercises the two real
resource omissions. `tests/unit/chrona/usecases/` or a focused CLI fixture
covers each typed class and guards unchanged unrelated failure handling.

No schema/resource migration or generated artifact is expected. Run focused
CLI and use-case tests, `git diff --check`, and
`tools/regenerate_public_examples.py --check --jobs 4` once as a batch. The
21 public materializers must remain byte-identical. Publish the code slice,
then inspect the CI three-OS full pytest/conformance, wheel/smoke and newest-
Python public-materializer jobs before acceptance.

## P2 — Release review

Record the exact implementation commit, focused commands, public-materializer
result, CI run and a direct evidence row for each of the three criteria in
`docs/reviews/current/issue-477-presentation-error-pointer-acceptance-review-2026-09-26.md`.
Publish separately, verify remote and close #477 only if every literal item is
met. A discovered contract or ownership gap sends P1 back to a published design
correction and implementation-plan amendment before code resumes.
