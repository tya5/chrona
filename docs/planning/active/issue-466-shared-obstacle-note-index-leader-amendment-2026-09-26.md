# Implementation Amendment — Index/Leader Independence (#466)

**Amends:** [O2 prerequisite plan](issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md) after the [design correction](../../design/issue-466-general-placement-note-index-leader-correction-2026-09-26.md) and [architecture review](../../reviews/current/issue-466-general-placement-note-index-leader-architecture-review-2026-09-26.md).

Refactor the annotation composition control flow so an optional note-index failure records its diagnostic and skips only index text/visual registration; leader routing always follows when the purpose requires one. Add a focused Layout test and retain the controller-z public integration assertion for all four leader IDs. Re-run affected annotation and materializer tests, inspect the SVG, then include this result in the O2 batch review.
