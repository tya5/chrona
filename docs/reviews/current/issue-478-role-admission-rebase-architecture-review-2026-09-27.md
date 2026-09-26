# Architecture Review — Rebased Role/Property Admission (#478)

**Reviewed:** [design correction](../../design/issue-478-role-admission-rebase-correction-2026-09-27.md)
against the [original design](../../design/issue-478-declared-treatment-visibility-design-2026-09-26.md),
Specifications 07/08/50/63/64, Theme v0.11/v0.12 schemas, #465 image-note
design, #466 candidate/annotation design, #426 axis tiers, #464 glyphs,
#429 catalogue, #391 capability ceiling, Theme inheritance and both closures.
This is a design review, not I478-3 release acceptance.

| Boundary | Finding and disposition |
| --- | --- |
| Theme / Scheme / inheritance | Effective Theme resolution remains the sole admission point. Checking direct declarations and Scheme targets separately preserves exact pointers; a resolved-map-only check would lose an overwritten declaration. No new Theme syntax or schema version is required. |
| Layout / assets | `annotationContainer` belongs to annotation-box Layout geometry. #465 image catalog pinning, content insets and representative fill are already specified and must not be reinterpreted as Scene paint or accepted on arbitrary roles. Nested token syntax and asset diagnostics stay with their current owners. |
| Scene / adapters | A role's permitted effect requires a capable completed primitive and serialization path. Shared Text/Icon and Path/Rect differences prevent a broad paint-property union. Adapters receive no role admission policy. |
| View / Project | No View or Project schema change, no new placement/label behavior. #466 candidate placement and #467 lanes remain independent; #478 only judges the Theme declarations reaching their existing consumers. |
| CLI / errors | `E_THEME_ROLE_PROPERTY_UNSUPPORTED` is a load-time error, distinct from I478-2 profile omission `info`. It preserves exact direct or Scheme source pointers through Draft and immutable closure. |
| Public resources / evidence | 24 current public Theme roots and 28 manifest slides supersede the old 15/21 count. Conformance fixtures are separate. Validator, source migration and generated evidence must publish atomically, with a structural census test and actual raster review. |

**Decision:** accepted for an I478-3 implementation-plan amendment, with no
change to I478-1/2 or the three literal issue criteria. The remaining risk is
role/consumer census completeness; an uncovered consumer is a design gap, not
permission to admit a broad exception. Public contexts must keep rendering
through the atomic migration. #476 closure and #466/#467 implementation are
not prerequisites for this correction.
