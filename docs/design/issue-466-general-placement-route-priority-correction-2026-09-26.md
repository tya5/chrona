# Design Correction — Semantic Route Priority Over Optional Plot Labels (#466)

**Predecessors:** [shared-obstacle design](issue-466-general-placement-design-2026-09-26.md), [comparison-host egress correction](issue-466-general-placement-comparison-egress-correction-2026-09-26.md).
**Discovery:** In the published HALCYON 03 artifact, ten dependency primitives are visible and one relation is suppressed. Wiring the single obstacle inventory while accepting optional member labels first leaves only four dependencies visible: the label below `vibration` blocks the short `vibration → tvac` corridor, and the finite alternate route exceeds the unchanged profile detour limit. This is a phase dependency, not a reason to relax route quality or silently accept new suppression.

## Selected phase contract

Layout separates **measurement** from **final placement**. It measures all text and uses the measured footprint when allocating rows and lanes; that fact does not require an optional plot label's final coordinates to be fixed. It then closes geometry in this order:

1. slots, rows, marks, ports, rule lines, required text and required rule labels;
2. semantic dependencies, using the shared inventory, finite endpoint candidates and the unchanged route quality limits; accepted route segments enter that same inventory;
3. optional plot/item/delta labels, whose existing ordered candidates query marks, required text, rules where applicable, and accepted dependency routes; accepted label text and visual footprints enter the inventory;
4. relation labels, then annotation boxes, text and leaders in stable order, querying all earlier relevant geometry;
5. decoration.

A required label whose placement is a precondition for a route remains in phase 1. Optional labels never veto an otherwise feasible semantic dependency. This is a declared priority between two independently visible families, not an obstacle exemption: later labels must still avoid accepted route strokes. If no candidate fits, the existing label overflow disposition applies and is diagnosed. A relation remains subject to the declared bend/detour/overflow policy. No hidden retry, second obstacle collection, new View syntax, or Theme behavior is introduced.

The ordered phases preserve one monotone `SurfaceObstacleIndex`. #467 lane packing may use measured label width in its collision-aware allocation, but final optional label coordinates follow the dependency phase. Where packing itself must account for a route, the lane design must declare a bounded allocation/reservation step rather than assume the old phase order. The exact public SVG/Scene byte changes, visible route count, and label diagnostics are acceptance evidence for this correction.

## Rejected alternatives

- Relaxing `maxDetourRatio` or allowing a route through accepted label glyphs changes the declared Layout policy.
- Exempting all labels during route search while leaving them in place permits visible overlap.
- Exempting a row or mark for an entire route violates the typed obstacle contract.
- Accepting six newly suppressed HALCYON 03 dependencies as a mechanical refactor would regress the public surface without a reviewed policy decision.

No resource schema migration is required. The public artifact may move optional labels; a label unable to fit must retain its declared overflow behavior and diagnostics.
