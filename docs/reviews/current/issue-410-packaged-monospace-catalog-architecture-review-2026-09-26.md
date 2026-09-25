# Architecture Review — Packaged Monospace Metrics Catalog (#410)

**Design reviewed:** `issue-410-packaged-monospace-catalog-design-2026-09-26.md`.
**Decision:** accepted for implementation planning.

## Boundary review

| Boundary | Required ownership | Result |
| --- | --- | --- |
| Context → Closure | Verify every declared family/weight, byte identity, and v3 metric identity before construction. | Pass |
| Closure → Layout | Supply a closed immutable catalog, not a default metric plus a fallback rule. | Pass |
| Theme → Layout | Theme selects only finite family/weight treatment; it supplies neither bytes nor metric data. | Pass |
| Layout → Scene | Select, measure, and record the exact asset before Scene construction. | Pass |
| Scene → adapter | Serialize completed family/weight/identity; register declared files without choosing a face. | Pass |

## Findings

1. A catalog is the minimal structural correction.  Passing one default metric
   while retaining a role-level family field makes a second declared face a
   false claim and would permit measurement/paint divergence.
2. The existing descriptor's closed `assets` collection is the appropriate
   extensibility point.  Adding a Noto Sans Mono asset does not require a
   second resource syntax or a Theme schema change.
3. The selected metric must be obtained before all shared measurement helpers,
   not only in `place_text`; otherwise table allocation or label fitting could
   choose geometry using Noto Sans and paint using Noto Sans Mono.
4. Missing selected family/weight is an immutable input error.  Reusing the
   default metric, allowing a trailing generic family, or asking an adapter to
   find a nearby installed face would violate the closure and reproducibility
   contracts.
5. Registering all closed font files with raster targets is compatible with
   their current `skip_system_fonts=True` policy.  Registration grants paint
   access only to declared bytes and never authorizes a target fallback.

## Required implementation controls

- Provide catalog selection tests for regular, bold, monospace, unknown family,
  and unknown weight.
- Trace the selected metric through every measurement helper and reject source
  scans that call a global default after resolving a treatment.
- Add the face, OFL notice, metrics import evidence, descriptor entries, and
  wheel-force inclusion together with the materializable Context migration.
- Test a public fixed-width role in Scene plus SVG and one raster/typeset
  projection.  Verify ordinary Noto Sans materializers remain unchanged except
  for declared resource closure identities.
- Keep system-font and glyph-substitute behavior unchanged; neither may serve
  as a catalog member.

## Conclusion

The design maintains the repository authority chain and is suitable for an
atomic implementation plan.  Any discovered need for an adapter or generic
fallback policy requires a return to design review rather than a local patch.
