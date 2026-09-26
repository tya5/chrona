# Design Plan — General Annotation Placement and Shared Obstacles (#466)

**Issue:** [#466](https://github.com/tya5/chrona/issues/466).
**Published baseline:** `4758fba70da53f4d966b3178142e10142dabe5b1`
on GitHub `main` (the [#467 lane design plan](issue-467-lane-packing-design-plan-2026-09-26.md)
is documentation only).

## Published facts and dependency

The current Layout composer has one fallback ladder, but rail and side rungs
call separate placement functions. Their obstacle inputs contain only prior
annotation boxes; leader routing also receives only prior boxes. By contrast,
plot labels already assemble mark and text obstacles locally. This is a
published ownership gap in Layout, not an adapter or Scene problem. The
published #413 correction intentionally made all four annotation purposes
share the ladder; this design must retain that semantic independence.

[#467](https://github.com/tya5/chrona/issues/467) needs a common obstacle
contract for packed item labels. The first independently useful #466 slice
is a typed surface obstacle inventory and consistent placement/leader query
API. It may publish before the full candidate/search/tail model, but that
partial publication does not satisfy #466 as an issue.

## Literal issue acceptance

1. One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it.
2. Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor.
3. A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line.
4. The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used.
5. Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count.
6. A Theme can draw the tail and balloon outline. A Theme without it renders as today.
7. The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it.

## Design questions

Define the surface-level obstacle identity, bounds/path geometry, collision
class, slot/region membership, paint/semantic role, and per-request exemption
rules. Establish when dependency paths, as-of lines, marks, labels, leaders
and annotation boxes enter the inventory. Avoid a causal cycle between a
route that needs labels as obstacles and labels that need the route as an
obstacle; specify finite phases or a deterministic fixed-point with a bound.

For the full issue, specify candidate data (region/search/obstacles/connector),
ordered fallback, compatibility of named rungs, typed View/Layout profile
ingress, bounded nearest-free enumeration and tie-breaks, as-of crossing,
leader/tail edge attachment, Theme treatment, Scene primitive projection,
adapter parity, diagnostics and migration. Review the no-refusal/visible-
overflow policy (#449), annotation-purpose independence (#413), source
identity, and label collision semantics (#467) against the whole design.

## Design and publication sequence

1. Publish this plan and characterize current label, annotation and leader
   paths, plus public evidence. Build a neutral dependency-line/annotation
   fixture and inventory likely materializer changes.
2. Publish a full selected design and whole-architecture review, including
   a bounded first slice for the shared obstacle inventory. Update living
   Specifications 06, 08, 33 and 44 as required before code. Record any
   intentional output changes; do not promise byte identity where obstacle
   correctness necessarily moves a note.
3. Publish an implementation plan with independent gates: obstacle inventory
   and query seam; candidate normalization with legacy-rung byte parity;
   nearest-free and fallback; tail/balloon Theme treatment; acceptance.
   The first gate may unblock #467 without closing #466.
4. Implement only approved slices. Run focused tests, public materializer
   checks and batched SVG/Scene raster inspection; let CI run full tests.
   Publish each coherent slice serially. Review all seven literal rows at
   issue completion and keep #466 open while any are deferred.

The #467 implementation plan may depend on the released obstacle seam, but
must not claim #466 complete or silently reimplement its candidate model.
