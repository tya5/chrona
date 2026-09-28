# #496 architecture review correction: pattern density

**Decision:** The density correction is consistent with the approved architecture.
**Design correction:** [basis-point density contract](../../design/issue-496-theme-asset-catalogues-design-correction-2026-09-28.md).
**Prior review:** [#496 whole-architecture review](issue-496-theme-asset-catalogues-architecture-review-2026-09-28.md).
**Normative authority:** [Specification 64 §8](../../specification/64-portable-icon-catalogs.md).

The correction represents density in the required `densityBasisPoints` field
as integer basis points and validates it from a deterministic 128×128
covered-center grid. It exactly encodes the
required 12.5%, 25%, and 50% ordered-dither entries as 1,250, 2,500, and 5,000
basis points. Half-up rounding is deterministic; a declaration inconsistent
with the normalized tile rejects at import.

The correction preserves Theme ownership of opaque substrate and ink, Layout
ownership of tile placement/clipping, the Scene v0.7 completed pattern value,
and adapter-only target serialization. It does not affect identities, closure,
schemas other than the documented density field, target capabilities, or the
explicit v0.4/v0.13/v0.14/v0.7 migrations. No further architecture change is
required. Update the implementation plan with the basis-point field and
focused density fixtures before product code starts.
