# Implementation Amendment — Residual Fit Closure (#457)

After publication of the [design correction](../../design/issue-457-residual-fit-correction-2026-09-26.md) and [architecture review](../../reviews/current/issue-457-residual-fit-architecture-review-2026-09-26.md), finish L2 of the [implementation plan](issues-457-447-fit-and-host-font-implementation-plan-2026-09-26.md) in independently testable pieces:

1. In `layout/surface_composer.py`, replace valid text-plus-icon inline
   shortages with natural-width placement and typed warnings. Test icon width
   greater than the assigned slot, a pre-reserved detail-panel run, and
   unchanged exact-fit public examples. Invalid icon geometry must diagnose
   at the input path.
2. In Layout canvas completion and SVG projection, include geometry before
   the requested origin. Test negative-origin text/icon placement and inspect
   the actual SVG viewBox, including the immutable path.
3. Record a source-site inventory for all remaining fit-named raises. For
   each, prove it is a caught candidate, invalid input/internal invariant,
   or convert it to a warning. Test one representative from each category;
   public materializer bytes, conformance, and the 63-case viewport matrix
   gate publication. Generated diagnostic inventories accompany source edits.

Each piece receives focused tests and a coherent serial push. CI supplies
the full three-OS pytest/conformance and newest-Python materializer gate;
no issue closes until the literal acceptance review has direct evidence.
