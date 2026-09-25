# Implementation Plan Amendment — I2 Typed Table Allocation (#403, #404)

**Precondition:** View v0.16 and I2 row allocation are published.

1. Create typed renderer-neutral column content and normalized widths at the
   review adapter; retain the named hierarchy column through presentation.
2. Replace positional input with typed measured allocation using the closed
   `content|fill|fr|minmax` grammar and declared overflow behavior.
3. Place headers/cells at declared alignment; indent only the named hierarchy
   column before fitting its text.
4. Remove first-column hierarchy branching and reject illegal allocations.
5. Add focused, Scene-boundary, and public materializer evidence; run full
   pytest and review generated differences before publication.

This completes only #403 width/alignment and #404 named hierarchy placement.
#389/#409 and #402 remain separate later slices.
