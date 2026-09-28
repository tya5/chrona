# #496 design correction: pattern density precision

**Corrects:** [selected #496 design](issue-496-theme-asset-catalogues-design-2026-09-28.md).
**Review:** [architecture review correction](../reviews/current/issue-496-theme-asset-catalogues-architecture-review-correction-2026-09-28.md).
**Normative authority:** [Specification 64 §8](../specification/64-portable-icon-catalogs.md).

The selected design left pattern density precision unresolved. A whole-percent
integer cannot encode the required 12.5% ordered-dither entry. Preserve exact
density in the required `densityBasisPoints` integer field from 1 through
10,000, where 100 basis points equal 1%. The importer counts covered cell centers on the fixed
128×128 grid after tile rotation and periodic edge wrapping, converts that
count to basis points with half-up rounding, and rejects any declared value
that differs. The starter dither densities are 1,250, 2,500, and 5,000 basis
points; 12.5% is not rounded to 13%.

This changes no tile geometry, Theme binding, Scene ownership, target, or
migration version. It corrects only the density representation and its
validation rule. The implementation plan must use this exact representation
and include boundary tests for all three ordered-dither densities.
