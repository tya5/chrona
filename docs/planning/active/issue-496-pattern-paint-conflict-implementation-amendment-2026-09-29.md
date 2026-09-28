# #496 Slice 2 pattern paint amendment

**Design/review:** [correction](../../design/issue-496-pattern-paint-conflict-correction-2026-09-29.md), [architecture review](../../reviews/current/issue-496-pattern-paint-conflict-architecture-review-2026-09-29.md). In Slice 2 closure validation, reject catalogue-pattern role stroke width/dash/finish, gradient, and non-fill background treatment with exact Theme pointers. Add one negative case per property family and retain existing non-catalog behavior. No Slice 3/4 scope change.
