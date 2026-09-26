# Architecture review — fallback-only candidate (#458)

**Correction:** [fallback-only design](../../design/issue-458-fallback-only-candidate-correction-2026-09-26.md).

Accepted. The refinement keeps #449's normal candidate ordering stable and
adds an explicit terminal rung only for a request that declares it. Layout
still owns geometry and Scene still projects the completed decision. All
other label requests retain first-ranked visible-overflow behavior. The
independent text-over-mark acceptance gate remains mandatory.
