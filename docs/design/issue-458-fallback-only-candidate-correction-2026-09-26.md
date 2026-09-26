# Design correction — fallback-only as-of seam candidate (#458)

**Predecessor:** [mark-clearance correction](issue-458-as-of-mark-clearance-correction-2026-09-26.md).

The first mark-clearance implementation moved ASTER's already-valid as-of
label because `above` entered normal candidate ranking. That violates the
bounded migration goal. The seam side is therefore *fallback-only*: normal
candidate ranking remains `(end, start, below)` and is unchanged for every
previously fitting as-of label. Only when all normal candidates are blocked
does Layout compute the declared `above` fallback. The fallback side must be
one of the finite supported side values, but need not be in the normal
candidate tuple. The resulting placement decision and text fallback ladder
record the extra side explicitly.

This remains a general typed Layout request capability rather than a
hard-coded Scene relocation. It changes only the previously suppressed or
mark-overlapping as-of cases; generated corpus diffs must prove the bound.
