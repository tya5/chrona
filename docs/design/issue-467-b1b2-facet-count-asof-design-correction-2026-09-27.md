# Design Correction — Counted Lane Members, Source-Keyed Mark Facets, and Actual Cutoff (#467, #494)

**Design plan:** [facet/count/cutoff plan](../planning/active/issue-467-b1b2-facet-count-asof-design-plan-2026-09-27.md). **Amends:** [candidate-footprint correction](issue-467-l3b-candidate-footprint-correction-2026-09-27.md) and [B1b-2 stroke-aware correction](issue-467-l3b-b1b-2-stroke-aware-footprint-correction-2026-09-27.md). **Normative home:** [Specification 38 §3.1](../specification/38-review-row-composition.md). **Architecture review:** [whole-architecture review](../reviews/current/issue-467-b1b2-facet-count-asof-architecture-review-2026-09-27.md). **Implementation plan:** to be amended after that review.

## Decision

A `LaneMember` represents one countable selected Review item: a host/root or an attached point. A same-object comparison facet is not a `LaneMember`, does not get a required duplicate label, and does not contribute to `LaneAssignment.members` or the lane-table item count.

Each `LaneMember.mark` carries an immutable collection of source-keyed mark facets. A facet is one emitted source primitive (including each glyph/icon path part where it is emitted separately) and contains:

- a stable facet/primitive identity scoped by the Review projection instance (`row_id` plus item ID, or the stable projected object instance in automatic mode), the facet purpose, and source kind; the stable source reference is a separate field;
- the stable source reference and semantic primitive role/type;
- the completed Layout geometry used for Scene projection, its renderer-neutral visible collision footprint, and its source ports with stable port identities tied to that exact projection instance where the primitive exposes ports;
- an explicit identity relation for every intentional within-bundle mark overlay.

Facets are grouped under their countable member, not flattened into anonymous `LaneMark.footprints` and not admitted as separately counted allocator members. The allocator validates and collides all facet footprints. It permits only explicitly declared overlay pairs among marks in the same atomic candidate bundle; all other internal overlaps are rejected as incomplete/invalid bundle closure. An overlay never exempts required labels, a different candidate, or a route. Glyph/icon child primitives retain their own identities while remaining part of their one semantic mark/member.

Only the candidate root and selected attached point item IDs enter `LaneAssignment.members`, `lane_of()` item membership, representative/predecessor identity, and `lane_preflight`'s lane-table count. The root determines candidate identity and representative identity. Attached points keep their own label and count identity, and are pinned to the root candidate's lane by the bundle. Comparison/Actual facets retain visual/source provenance within the relevant countable member.

The B1b-2 Layout mapper receives the selected cutoff explicitly as a validated `as_of: date | None` argument from the existing normalized `PresentationContract.time.as_of`. It does not read Actual resources and does not copy the cutoff into `ReviewProjection`. If a selected member has `actual.openUntil == "asOf"` and `as_of` is absent, mapping fails before allocation with `E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE` and the item/role path. The final composition consumes the same contract cutoff and the exact completed geometry closure retained by the lane plan.

## Geometry and identity invariants

1. The projection-instance identity (View row ID plus item ID, or the stable projected object instance in automatic mode), source reference (stable source/object), source kind, facet purpose/identity, generated lane identity, and generated placement identity are distinct. A repeated source/object in two explicit rows therefore has distinct facet and port identities while retaining the same source reference. Generated lane IDs never replace source or primitive provenance.
2. A facet owns the association between one completed primitive, its obstacle footprint and its ports. `ObstacleRect` coordinates already include the approved visible stroke expansion; `ObstacleSegment` keeps the centerline and carries its stroke width once. Collision clearance remains separate.
3. Layout uses the same Theme geometry role, mark variant, temporal scale, normalized icon closure, and icon stroke scale as final composition. For stroked path control-point envelopes it applies the approved 10× stroke-width-per-side bound. No Scene paint is resolved or mutated in Layout.
4. Progress is a clipped child visual with its own stroke treatment when present; it is neither an independently counted member nor a second expansion of its host. Raster icons reserve the viewport; vector icon path facets preserve asset/path identity and transformed commands.
5. The plan's source-keyed facets are the sole B2 projection authority. B2 MUST project the completed paths, ports, and primitive identities from that closure and MUST NOT recompute them from `ReviewProjection`, Theme, icon payload, a second scale, or Scene state. Every port and primitive maps to one exact projection instance even when its stable source/object is repeated in multiple explicit rows. A final-contract cutoff mismatch is a typed pre-output failure, not a reason to rebuild marks.
6. Missing or invalid required geometry and invalid source-to-facet associations fail before allocation with `E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE` or the existing stable Theme diagnostic. They are not converted into a lane-fit rejection and no facet is silently omitted.

## Layer connections and migration

Projection and `PresentationContract` supply selected semantic items, comparison/attachment intent, Actual facts and cutoff. Layout maps those to immutable countable members and source-keyed completed mark facets; the neutral allocator need not load Project/View/Actual resources or understand paint. Scene consumes Layout placements and invokes the existing paint resolver; adapters serialize the completed result. Theme and icon resources remain appearance/geometry sources, not sources of item count or generated lane identity.

The correction changes only internal Layout values and the normative description of their identity/count semantics. It changes no Project, View, Actual, Theme, Scene, or adapter schema, and no public lane activation is allowed in B1b-2. Lane assignment may change when previously anonymous/missing facets are represented, and lane counts become explicitly counts of root/attached Review items. Repeated source/object instances in explicit rows retain distinct projection-instance and port identity under Specification 38. Existing `automatic` and `explicit` selection, geometry, output bytes, and path remain unchanged. The public lane guard stays closed until L3c.

## Alternatives considered

- A comparison as a regular `LaneMember` was rejected because the current allocator includes every member in `LaneAssignment.members` and the preflight count is `len(lane.members)`. It duplicates item counts and placement/label semantics.
- An anonymous rectangle/segment tuple appended to the root mark was rejected because it loses which Review source and primitive produced each footprint and which ports B2 must expose.
- A parallel provenance table was rejected for this correction: it can drift from the footprint sequence used by collision checks. Keeping the provenance, completed geometry, ports and footprint together in one immutable source-keyed facet makes identity and geometry atomic.
- Copying `as_of` into `ReviewProjection` or loading the Actual Set in Layout was rejected. The existing normalized `PresentationContract.time.as_of` is already consumed by Layout and is the single selected cutoff; pass that validated value explicitly to the mapper.
- Reconstructing paths in Scene or from the final manifest was rejected because it breaks the preflight-to-B2 source/geometry invariant and can apply transforms/strokes twice.

## Required implementation evidence

The successor implementation amendment must test source-keyed identities, primitive/part uniqueness, port retention, overlay-pair validation, countable member lists/table counts, representative/predecessor behavior, deterministic order, attached pinning and separate attached labels. It must cover open Actual with and without a cutoff, closed/point/missing Actual, progress, point/glyph/vector/raster geometry, exact S1 path closure, 10× path bound and separate clearance. An allocator-to-preflight-to-B2 fixture must prove the same immutable facet closure is collided, counted correctly and realized once. The public guard and automatic/explicit byte characterization remain gates. The six #467 and three #494 literal acceptance criteria remain open.
