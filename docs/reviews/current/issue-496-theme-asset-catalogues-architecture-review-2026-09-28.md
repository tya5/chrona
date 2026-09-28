# #496 Theme asset catalogues architecture review

**Decision:** Design approved as the basis for implementation planning.
**Design:** [selected #496 design](../../design/issue-496-theme-asset-catalogues-design-2026-09-28.md).
**Plan and literal acceptance:** [#496 work record](../../planning/active/issue-496-theme-asset-catalogues-work-record-2026-09-28.md).
**Base:** `bbe6734fa8a4db25f6b87c088262163f1bc840dd` (`origin/main`).
**Design publication:** `03551c355d51d173cbe52228658d3d4bba2a1ce1`.
**Correction review:** [pattern density precision](issue-496-theme-asset-catalogues-architecture-review-correction-2026-09-28.md).

## Architecture findings

The shared catalogue preserves Spec 64's immutable identity, local import,
licence/notice closure, and `set:name` lookup. Reusing the resource kind and
Context field avoids a second acquisition or closure mechanism. Explicit
catalogue and preset-library version migrations keep closed schema behavior;
Theme v0.13/v0.14 and Scene v0.7 isolate newly authored and completed values
from current Theme and Scene contracts.

Ownership aligns with Specs 06/07/08/33/46/50: Theme selects assets and paint;
Layout completes bounds, tile origin, and clipping; Scene carries only closed
completed tile and paint values; adapters serialize them. SVG may express
periodic repetition natively, and PNG derives from the same SVG. This keeps
renderer syntax out of Theme/catalogue data while allowing exact SVG/PNG parity
evidence. The two ScenePaint channels expose substrate/ink to existing contrast
and perceptibility gates.

View and Style do not gain asset selection or semantic meaning. Glyphs remain
mark geometry under #464. Existing icon accessibility and textual equivalence
remain governed by Spec 64. Pattern bindings extend only registered Theme
role/property consumers; unsupported roles fail before Scene. Theme v0.13
introduces no semantic roles.

Preset integration preserves #470's project-generic resource bundles and
Spec 28 legend ownership. Existing preset v0.1 already closes catalogue
references, so only builtin-library v0.2 and its copy/materialization boundary
change. `render --preset` consumes that explicit closure. Spec 62 stays
proposed: the approved v0.4 catalogue can later be an ordinary verified static
member, but this design grants no registry, acquisition, or resolver behavior.

The design also respects Spec 63 and ADR-0018 target admission: only SVG and
the pinned resvg PNG route are in scope. It does not widen PDF, Typst, TikZ,
raw SVG, general images, filters, or rich paint. #465 container PNG assets
retain their existing bytes and Theme-owned insets.

## Decision and gates

Approve for implementation planning. Before product implementation, the plan
must allocate separately reviewable catalogue/import, Theme/Scene/paint, and
preset/starter-resource slices. Required evidence includes schema and
resource-registry conformance, atomic import failures, exact Theme pointers,
closure/copy with notices, current public SVG and PNG materializers, byte and
decoded-pixel comparisons, and contrast/perceptibility witnesses for both
pattern channels. A passing unit test alone does not satisfy user-visible
acceptance.

No product implementation or release acceptance is approved by this design
review. Outstanding implementation facts are builtin asset provenance and
notices, actual adapter parity, and rendered evidence. The issue remains open
until every literal acceptance statement in the work record has direct release
evidence.
