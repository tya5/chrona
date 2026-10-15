# #1373 row 3: architecture review

Decision: design complete; input slice published, physical allocation in progress.
[Plan](../../planning/active/issue-1373-hosted-points-design-plan-2026-10-15.md) ·
[Design](../../design/issue-1373-hosted-points-design-2026-10-15.md) ·
[Normative contract](../../specification/50-constraint-driven-gantt-surface-quality.md#35-physical-point-hosting-1373).
Baseline: published READY `7c46a7c695ed0863d17998acad062923f7acc4e1`.

| Boundary | Review conclusion |
| --- | --- |
| Project/View, Specs 06/38 | Preserve author links per source separately from row-derived attachment; no schedule, selected row, member or hierarchy change. Direct parent only; reviewer-approved precedence and inclusive interval retained. |
| Theme, Spec 07 | Existing symbol dimensions/parts/ink remain authoritative; no fit shrink or project-specific palette. Actual-ground mark contrast remains enforced. |
| Layout, Specs 33/50 | Resolve eligible facet identities once; separate semantic inventory from physical allocation and use one host-relative frame in preflight and final composition. Exact point/host overlap is not a lane-membership relaxation. |
| Windows and comparisons | Source/scenario/facet identity and original dates govern eligibility; existing child window admission governs emission. Missing/hidden hosts do not gain paint or ports. |
| Labels | Physical row owns placement demand/band; child retains semantic ownership and provenance. No stale own-row association after moving its point. |
| Routes and annotations | Explicit exact-host egress only, reciprocally for a span endpoint covered by its exact hosted point; other hosted points remain obstacles. No route-body exemption or different-object comparison-cluster pollution. All recovery callers retain the relationship. |
| Scene/adapters, Specs 08/49 | Completed ordinary geometry and paint order only; no host lookup, measurement or coordinate correction downstream. |
| Schema, Spec 56 | Optional v0.10 insertion, explicit runtime default-off, shared parts unchanged. No Project/View/Scene schema migration. |

Independent read-only review first found a genuine preflight gap: whole-instance
lane subtracks could not represent a point physically hosted in another lane.
The selected design resolves it with an allocation-only facet partition, explicit
hosted-only accounting and final-frame equivalence. Re-review found no remaining
architecture blocker or mismatch with reviewer6184233415.

Consumer review found that legacy `ConnectorEgress.host_ids` is passed to
whole-route reduction and recovery. Adding physical neighbours to that field
would violate the endpoint-only contract. The current design separates physical
corridor authority and splits full-route segments at recorded exposed boundaries;
body checks and recovery retain those obstacles. This stays wholly in Layout,
preserves existing comparison behavior and changes no public policy or schema.
Required evidence includes reduced collinear terminal segments, setbacks,
reciprocal endpoint coverage, route-body re-entry, hints and annotation fanout.

Release risks to verify, not completed claims: cross-row labels/dependencies;
planned/Actual/snapshot/scenario isolation; duplicate occurrence ambiguity;
source-facet partition and ports/parts/window equivalence; fixed glyph collision;
actual SVG/typeset and default-off public materializer evidence. Both prerequisite
publications are complete. Final-frame proof and non-lane collision tests now
pass; acceptance remains subject to current-head CI and exact-main release.
