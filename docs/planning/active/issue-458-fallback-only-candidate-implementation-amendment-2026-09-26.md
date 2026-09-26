# Implementation amendment — fallback-only candidate (#458)

**Correction:** [fallback-only design](../../design/issue-458-fallback-only-candidate-correction-2026-09-26.md).

Modify `layout/labels.py` so an explicitly declared fallback side is a
terminal rung outside the normal candidate tuple. Keep the as-of tuple at
`(end, start, below)`, record `above` in the placement ladder, and prove
unchanged output for formerly fitting corpus labels. Re-run all public
materializers and the complete generated-output property suite before
publishing code.
