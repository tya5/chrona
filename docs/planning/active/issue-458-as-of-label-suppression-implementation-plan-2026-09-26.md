# Implementation plan — as-of label placement (#458)

**Design:** [#458 design](../../design/issue-458-as-of-label-suppression-design-2026-09-26.md).
**Review:** [architecture review](../../reviews/current/issue-458-as-of-label-suppression-architecture-review-2026-09-26.md).

1. In `layout/surface_composer.py`, give the as-of label visible-overflow
   placement. In `scene/v05_builder.py`, filter all suppressed text projection
   through the same typed rule, not a special-case as-of branch. Test normal,
   overflowing, and explicitly suppressed neutral placements. Publish the
   implementation with regenerated 04/07 public SVG/Scene evidence.
2. In `scene/perceptibility.py` and focused tests, compare exact suppressed
   diagnostic placement IDs with emitted primitive IDs. Run the corpus gate;
   no committed Scene may violate the invariant. Publish independently if
   the first slice is accepted.
3. Run focused Layout/Scene/CLI tests, public materializer byte checks,
   conformance, and batch SVG/Scene diff inspection. CI supplies full pytest,
   wheel/smoke and newest-Python reproduction. Record literal acceptance rows
   and exact CI/commit evidence before closing #458.

No schema migration. Unexpected generated changes or a new suppression
identity mismatch return to design before implementation continues.
