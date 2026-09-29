# Issue #554 — Leader obstacle Scene schema correction

**Corrects:** [member-label leader design](issue-554-member-label-leader-correction-2026-09-29.md). The completed leader path participates in the typed lane obstacle inventory as `leader-route` stroked-segment facets. Both published Scene v0.6 and v0.7 schemas currently enumerate only `mark` and `required-label`, so valid completed lane Scenes fail serialization.

Add `leader-route` to `laneObstacle.class` in both schema versions. It denotes only the footprint of a completed member-label leader Path, retains the same primitive/member identity closure as other facets, and does not introduce a new geometry kind, route policy, adapter inference, or Scene version. The Scene model and Layout already carry this value. Retain exact cross-reference validation. A leader-bearing public materializer must serialize and validate its Scene and SVG; a no-leader Scene stays byte-stable except for intentional #554 changes.
