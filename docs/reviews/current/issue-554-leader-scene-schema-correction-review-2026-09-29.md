# Issue #554 — Leader Scene schema correction review

**Decision:** approve the [schema correction](../../design/issue-554-leader-scene-schema-correction-2026-09-29.md) before the release slice. HALCYON 02 produces three `leader-route` facets; schema validation alone rejects them, while finite-value and cross-reference closure checks pass.

Specs 08 and 38 require Scene to expose completed Layout geometry and typed lane/member ownership. Enumerating the already-designed leader footprint aligns the public schema with those contracts. Spec 50 still owns the Layout route; Scene and SVG only project it. No Project, View, Theme, Context, or adapter migration is required. Both supported Scene schema versions must be amended together, then a leader-bearing serialized Scene and public SVG must be checked. Do not weaken reference closure or silently drop obstacle facets.
