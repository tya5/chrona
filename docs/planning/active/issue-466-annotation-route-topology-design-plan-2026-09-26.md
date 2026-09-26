# Design Plan — Annotation Route Topology After Shared Obstacles (#466)

**Public baseline:** `07f55068` contains O1 and design documents. O2 product code is not published or accepted. The [non-acceptance review](../../reviews/current/issue-466-bounded-escape-nonacceptance-review-2026-09-26.md) records the controller-z failure. The exact form of a clean connector/candidate contract is unverified.

## Literal #466 acceptance ledger

1. One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it.
2. Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor.
3. A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line.
4. The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used.
5. Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count.
6. A Theme can draw the tail and balloon outline. A Theme without it renders as today.
7. The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it.

## Design questions and slices

The immediate gate is item 1 without regressing public rail layouts. Determine whether the route/box pair must be solved jointly, whether dependency/leader crossings need an explicit bridge or paint relation, and whether a candidate may reserve a connector corridor before its box is final. Keep all alternatives on one typed inventory; do not silently remove marks/text/routes from collision queries. Compare the controller-z topology, the Sunday Strip in-plot balloon target, and #467 packed-row label geometry against the same rule.

1. Map obstacle and connector topology for controller-z, HALCYON 02/03/04 and a neutral note-beside-dependency fixture. Record which accepted geometry forms an unavoidable barrier and which is only a router limitation.
2. Select a finite placement/search/connector contract, including whether crossing is ever legal and how Scene paints it. Define identity, candidate count, fallback, boundedness, diagnostics and migration. Review against the whole Project → View → Theme → Layout → Scene → adapter architecture and adjacent specifications.
3. Publish design, living specification/ADR and architecture review. Amend the O2 implementation plan with independently testable slices before product code resumes.
4. Require rendered public SVG/Scene batch comparison and three-OS CI acceptance; a green structural test alone cannot accept a visually harmful route.

No #467 implementation may consume an unaccepted O2 annotation behavior. #467 feasibility work may use the published O1 types as read-only input, but implementation/publication follows the resolved dependency.
