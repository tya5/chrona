# Design Correction — Draft Host Cap Height (#447)

**Predecessors:** [combined design](issues-457-447-fit-and-host-font-design-2026-09-26.md), [numeric-capability correction](issue-447-host-numeric-capability-correction-2026-09-26.md).

The real Ubuntu fontconfig gate selects exact DejaVu Sans 400 and 700 faces,
but their OS/2 tables have no positive `sCapHeight`. The shared metrics
extractor rejects them before Layout. This is a measurement-contract gap,
not a face-discovery failure. The published `f5061e59` CI run proves it.

For an explicitly requested volatile Draft host face only, use the font's
positive `sCapHeight` when present. Otherwise derive cap height from the
selected face's uppercase `H` outline: resolve `H` through that face's Unicode
cmap, obtain its glyph bounds with fontTools, and use its positive top bound in
font units. Reject a missing glyph, empty outline, nonpositive or out-of-range
top bound with `E_FONT_SYSTEM_MISMATCH`; do not substitute an ascent, another
font, or an estimated percentage. Read the same TTC face index used for
identity, metrics, and paint. The derived value is volatile measurement data
for this Draft render only, not a persisted declared-metrics artifact.

Immutable declared font imports keep the existing positive OS/2 `sCapHeight`
requirement. The on-disk v3 metrics schema and exact `(family, weight, bytes,
face index)` identity are unchanged. The derivation is in font closure before
Layout; Layout sees the completed metric, while Scene and adapters remain
projection-only. Existing valid `sCapHeight` takes precedence, so previously
materialized examples and ordinary host faces do not change.

## Whole-architecture review

This closes the Draft-only exception to Specification 30's declared-metrics
rule without allowing host lookup into an immutable Context. It is compatible
with Specifications 08/13/33, #411's volatile ingress, #448's multi-face
closure, and the #447 numeric-capability correction. The resulting metric is
still derived from one exact face. A glyph-outlines dependency remains limited
to the ingress metric extraction; neither Layout nor a renderer measures it.
The risk is that an unusual face lacks `H`; exact rejection remains preferable
to a silent metric substitution.
