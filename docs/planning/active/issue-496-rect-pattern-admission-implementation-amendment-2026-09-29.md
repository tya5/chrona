# #496 Slice 2 Rect pattern amendment

**Design/review:** [correction](../../design/issue-496-rect-pattern-admission-correction-2026-09-29.md), [architecture review](../../reviews/current/issue-496-rect-pattern-admission-architecture-review-2026-09-29.md). Amend the [implementation plan](issue-496-theme-asset-catalogues-implementation-plan-2026-09-28.md) only for Slice 2.

Theme v0.13 admission, capability tests, Layout pattern placement, and Scene v0.7 projection cover exactly the ten always-Rect pairs in Specification 07. Add negative tests for each excluded mixed/Symbol family with exact Theme pointer, plus positive Rect and SVG/PNG tests. Slice 3's starter preset uses a safe Rect role for its pattern and a point mark for its glyph. No change to the issue's five literal acceptance criteria or Slice 4 gate.
