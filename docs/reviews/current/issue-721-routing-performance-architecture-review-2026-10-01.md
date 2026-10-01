# Issue 721 item 2: routing performance architecture review

**Scope:** design review only, not the issue acceptance review.
**Design:** [issue-721-routing-performance-design-2026-10-01.md](../../design/issue-721-routing-performance-design-2026-10-01.md)

| Question | Finding |
| --- | --- |
| Layer ownership | The index lives in Layout (`presentation/layout/obstacles.py`), which already owns completed geometry and routes. Scene and adapters are untouched; no import direction changes. |
| Public API and schemas | No new public name, schema, diagnostic, CLI option or specification text. The cache and grid are private to `SurfaceObstacleIndex`. |
| Determinism | `collisions` returns the same ordered tuple, so A* sees the same boolean per segment and expands in the same order. Candidate positions are sorted, never iterated from a set or dict. |
| Float behaviour | The unchanged predicates run on the unchanged doubles. The grid uses comparison and `floor` only, plus a slack that makes it a superset filter. Nothing reorders or fuses arithmetic that reaches geometry, so results are identical across Linux, macOS and Windows. |
| Monotone index | The index is append-only per surface; `add` invalidates the private cache. Fresh per-candidate indexes (annotation search) do not pay a grid build until repeatedly queried. |
| Corpus data | No corpus input or expected output is edited; byte identity of every committed Scene and SVG is the proof, which AGENTS.md accepts for a no-behavior-change slice. |
| Alternatives rejected | (a) Reducing A* work or the visibility grid: can change equal-cost tie-breaks, a behaviour change. (b) Memoizing `clear()` per segment: helps little (segments rarely repeat within a call) and hides cost rather than removing it. (c) An R-tree or sorted-interval structure: more code for about 100 obstacles per call; a grid plus cached envelopes removes the measured cost (select, envelope recomputation, overlap scan) with less risk. |
| Residual risks | A conservative-slack mistake would drop a real collision; covered by the property test with boundary and ulp cases and its mutation check, and by byte identity of the corpus. Remaining cost after the change (segment construction, A* bookkeeping) is reported with the measured speedup, not hidden. |
| Verdict | Approve slice I721-2b. |
