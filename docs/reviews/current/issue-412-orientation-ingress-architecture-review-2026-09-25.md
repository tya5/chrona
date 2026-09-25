# Architecture Review — Orientation Ingress and Completed Geometry (#412)

**Reviewed design:** `issue-412-orientation-ingress-correction-2026-09-25.md`
**Result:** accepted for implementation planning.

## Boundary review

| Boundary | Decision reviewed | Result |
| --- | --- | --- |
| View -> normalization | v0.18 exposes closed axis-label and table-header intent only; normalized records are typed. | Pass |
| Profile -> Layout | v0.8 separates review-surface `flowDirection` from graph-only `dependencyNetworkFlowDirection`. | Pass |
| Layout -> Scene | Layout completes the finite orientation, exact degree, pivot, and physical bounds before Scene. | Pass |
| Scene -> materializer | Scene v0.5 transports the pair; adapters serialize supplied degrees/pivots only. | Pass |
| Table/axis -> geometry | Column minima and tier lanes consume occupied dimensions, including header-row reservation. | Pass |
| #412 -> #404 | Group-column work consumes the one completed text pipeline later; it does not create another orientation convention. | Pass |

## Findings

1. Replacing `writingMode` is required, not cosmetic.  Its current vertical
   values affect only dependency-network node axes and falsely imply a text
   capability.  A single renamed field would still conflate two owners.  The
   two v0.8 declarations preserve the real graph behavior while truthfully
   narrowing review-surface flow.
2. A finite View ingress is necessary.  A generic `transform` field would let
   content choose geometry without semantic ownership, invite arbitrary angles,
   and make later label kinds bypass the contract.  The selected axis-label and
   header locations match the actual #412 use cases; group headers remain #404
   scope.
3. Width/height exchange alone is insufficient.  Rotation about a baseline
   changes the occupied rectangle's origin as well as its extent.  The
   four-corner calculation prevents a class of apparently fitting labels that
   paint outside their lane.  It also makes collision, clipping, and adapter
   transforms auditable from one completed value.
4. Table headers must reserve physical block space before row placement.  The
   current layout measures headers only as inline strings.  Retrofitting an
   adapter transform would overlap the first row; retrofitting a table-only
   height tweak would duplicate the general orientation geometry.  The design
   instead routes both through Layout's completed text measurement.
5. Requiring a Scene version boundary is appropriate.  A required angle cannot
   be added to a live schema as an optional compatibility default without
   leaving Scene consumers ambiguous about whether a transform was omitted or
   intended to be horizontal.  v0.5 makes the no-inference contract machine
   checkable.

## Cross-design consistency

* The placement-foundation rule remains intact: Scene projects placements and
  contains no font metrics, text fitting, layout routing, or transform choice.
* #410's `TextTreatment` remains presentation treatment.  Orientation is not
  a Theme role because it changes occupied geometry and feasibility.
* #405's axis density work continues to own form selection and thinning.  This
  correction adds physical occupied measurement to its existing decisions; it
  does not silently prefer rotation or alter its declared overflow policy.
* #404's group-as-column composition may use `place_text` after it defines the
  group semantic source and column reservation.  It must use v0.18's finite
  vocabulary or a future versioned semantic ingress, never an adapter escape
  hatch.
* #411's draft font resolution remains orthogonal.  The same resolved metrics
  feed rotation measurement, but host selection never reaches a serialized
  orientation/geometry contract.

## Required implementation safeguards

1. Put orientation-to-degree mapping and four-corner occupied-bounds math in
   one Layout helper.  No schema parser, Scene builder, or adapter may recreate
   it.
2. Make `TextPlacement` and `TextLayout` validate the finite orientation/angle
   pair.  Ensure constructed existing horizontal placements carry explicit
   zero, rather than relying on an implicit adapter default.
3. Evolve `axis_label_fits` from a scalar-width predicate to a completed
   measurement predicate, and reserve each accepted label lane before placing
   it.
4. Evolve `place_table_columns` through a typed measurement result or explicit
   header measurement callback; do not infer header orientation from a column
   identifier or pass an untyped optional map.
5. Build structural tests that fail if `scene/` imports the orientation geometry
   helper or if an adapter imports font measurement.  Add target snapshots that
   assert degree/pivot passthrough, not merely a visual substring.
6. Regenerate public evidence in one batch after all schema migrations and
   distinguish intentional rotation/scene-version deltas from unrelated bytes.

## Residual risks and dispositions

| Risk | Disposition |
| --- | --- |
| SVG, Typst, and TikZ use different transform syntax | Use target-specific serialization tests against the same Scene angle; syntax is projection, not policy. |
| Existing layout slots may not have block room for rotated axis/header labels | Treat as declared Layout overflow or update the designated fixture's slot contract; never allow spill. |
| Automatic axis labels could select a form on unrotated width | Run candidate fitting through occupied measurement and total lane allocation before selection. |
| Future CJK requirements are mistaken for this capability | Schema description and tests explicitly call the result rotated horizontal text only. |

## Review conclusion

The correction resolves the missing input and output contracts without
collapsing View, Layout, Scene, and adapter responsibilities.  It is safe to
replace the earlier I412-1 outline with a detailed implementation plan.  Any
need for an additional label category, non-right-angle transform, vertical
shaping, or different surface axis model requires a new versioned design
decision before implementation.
