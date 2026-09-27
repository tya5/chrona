# Design Amendment — Reuse the Icon Catalogue, No New Resource Kind (#465)

**Corrects:** the [design](issue-465-image-annotation-container-design-2026-09-27.md)'s
Contract 1 and its "asset family" references in Contracts 2 and 4 and
Migration. **Decision:** lead-approved with this one change, 2026-09-27.
**Supersedes:** Specification 65 (withdrawn; see
[Specification 64 §7](../specification/64-portable-icon-catalogs.md#7-container-artwork-exception-465)
and the [Specification 07 update](../specification/07-style-and-theme.md)).

## What changes

Contract 1 ("a new sibling asset family") proposed
`chrona/container-image-catalog/v0.1` and a `render-context/v0.17`
`containerImageCatalogs` input, reasoning that spec 64's own boundary
("does not own... arbitrary images/artwork") and its View-cannot-bind
requirement made a new resource kind necessary. The lead rejects this: it
is not the smallest contract, Contexts already pin icon catalogs (identity
and closure) through `iconCatalogs`, and a Context version bump would
migrate every committed Context for no reader-visible gain.

**Corrected Contract 1:** the container's backdrop artwork is an ordinary
`chrona/icon-catalog/v0.3` raster PNG entry (spec 64 §2's existing
"purpose-built PNG entry bytes"), referenced by the Theme's
`annotationContainer.image` field using the same `<set>:<name>` form a
View's `visuals` grammar already uses for icons. No new resource kind,
schema, or Context input is introduced. "A View cannot bind it" is
unaffected — it never followed from the asset's storage location, only
from the fact that no View field reads `annotationContainer`. A View
naming the same catalog entry as an ordinary icon selects a companion
beside a label or over a mark; it does not, and cannot, become the
annotation's container, because nothing in the View schema names
`annotationContainer` at all. The two are independent selections of one
closed asset, exactly as two different icon placements in the same View
can already name the same entry.

**Corrected Contract 2 (Theme `annotationContainer.image`):** unchanged in
every field (`image`, `sliceInsetsEm`, `contentInsetEm`, forbidding a
non-zero `cornerRadius`). Only the resolution target of `image` changes:
it resolves against the Context's pinned `iconCatalogs` closure (already
verified before Theme/Layout today), not a new closure. `ThemeTokenView.
annotation_container`'s new branch now needs the same icon-catalog
resolution path `theme_tokens.py`'s icon-adjacent callers already use,
not a new one.

**Corrected Contract 4 (Scene/adapters):** unchanged. `ScenePaint.image`
still carries `asset_identity`, `viewport`, `payload` (PNG bytes,
in-memory only), and the completed tile list; the identity now happens to
be an icon-catalog entry's identity, which the Scene layer already treats
as an opaque string.

**Corrected Migration:** "`chrona/render-context/v0.17` is additive" is
withdrawn. No Context schema version changes for #465. A Theme
`outline: image` binding that names an entry outside the pinned
`iconCatalogs` closure is the same ingress error described in the original
design (exact diagnostic id unchanged in intent), just checked against the
existing closure instead of a new one.

**Unaffected:** Contract 3 (Layout content box/paint box split, nine-slice
geometry), the "why not a dedicated primitive kind" section, Diagnostics
(apart from the closure it checks against), and Tests. All proceed exactly
as designed.

## Why this is still one container mechanism, not two

An image-backed container remains a `Rect`/`Symbol` Scene primitive with an
additive `ScenePaint.image` fill mode, exactly as designed. What changes is
only where the artwork's bytes live before Layout ever sees them — and that
was already the one place icons live. This is a smaller contract than the
withdrawn sibling-resource-kind design, not a different one.
