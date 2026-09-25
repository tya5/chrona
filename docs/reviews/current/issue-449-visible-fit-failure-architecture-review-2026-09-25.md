# Architecture Review — Visible Fit and Placement Failure Policy (#449)

**Decision:** accepted for implementation planning.
**Reviewed design:** `issue-449-visible-fit-failure-policy-design-2026-09-25.md`.

## Boundary review

| Boundary | Accepted responsibility | Rejected responsibility |
| --- | --- | --- |
| Project / View / Profile | Closed content facts and author-selected exceptional disposition | Coordinates, implicit target-specific fit choices, or an unstated default suppression |
| Theme / font assets | Declared typography and metric inputs | Whether an item is retained, overflowed, or hidden |
| Layout | Measurement, candidate ranking, visible fallback geometry, completed canvas and ordered warnings | Serialization or a renderer-specific crop workaround |
| Scene | Verbatim projection of placements, canvas and warning records | Measurement, collision recovery, canvas growth, routing, or disposition selection |
| Renderer adapters | Serialization of the completed canvas and primitives for their target | Reflow, clipping, omission, warning-policy inference, or a target-specific fallback |

The proposed flow retains the completed Layout → Scene seam from ADR-0031 and
Specification 08.  It is therefore a feasibility-policy correction, not a
second geometry authority.

## Findings and resolutions

1. **The old `diagnose` value cannot remain as a compatibility spelling.** Its
   prior externally observable meaning was refusal, directly contrary to #449.
   The design correctly replaces it atomically with `visible-overflow` and
   removes the old reader.  This agrees with the repository's clean-migration
   policy.
2. **A visible slot escape is insufficient if the outer target clips it.** The
   completed `canvas_bounds` requirement is necessary.  The implementation
   must pass those bounds from Layout through Scene into every renderer rather
   than allow SVG's incidental overflow behavior or raster/PDF cropping to
   decide visibility.
3. **The ordinary mark-containment check remains a useful measurement
   predicate, not a reason to reject.** It must feed the specified natural
   mark placement and `W_LAYOUT_MARK_OVERFLOW`; it may not be globally deleted
   or converted into a Scene exception.
4. **Previously completed axis thinning needs correction.** The default path
   must place all labels; `thin-with-record` remains an explicit View choice.
   This is a functional change and requires regenerated visual evidence.
5. **Warnings must be structured before they reach Scene.** A string-only
   diagnostics tuple cannot satisfy #449's placement and extent requirements.
   The implementation must introduce one typed record and a versioned Scene
   serialization migration, not encode ad-hoc colon-delimited fields.
6. **Not every literal Layout exception is a fit/placement refusal.** Schema,
   resource, identity and invalid metric input retain error semantics.  The
   implementation plan must maintain a source-derived allowlist/classification
   test for every user-reachable member of the measured diagnostic families,
   including `E_LAYOUT_RELATION_UNROUTABLE` where it is the route family’s
   current public spelling.

## Specification and ADR alignment

ADR-0031 currently says that `diagnose` fails before Scene, and Specification
50 currently requires all required geometry to remain in slots and
non-intersecting.  Those statements conflict with the owner decision and must
be amended in the first implementation slice, together with the type/schema
contract.  The no-Scene-measurement and no-adapter-policy rules in ADR-0031,
Specification 08, and Specification 50 remain sound and are strengthened by
the completed-canvas requirement.

## Required implementation safeguards

- A structural test rejects any user-reachable fit/placement path that maps a
  valid closure to `RenderFailed`.
- A registry test gives every current public failure family one fallback,
  warning code and completed-placement evidence.
- Renderer contract tests prove SVG, PNG, PDF, Typst and TikZ consume the same
  supplied canvas bounds; no adapter may select a fallback.
- Migration tests prove no live `diagnose` declaration or retired profile
  identity is accepted.
- The release review must compare regenerated SVG/PNG output and confirm that
  all expected scene warnings are serialized.

With these safeguards, the design improves artifact availability without
reintroducing hidden loss, geometry ownership drift, or target-dependent
behavior.
