# Design Correction — Completed Paint Order Must Reach Every Adapter (#439)

**Corrects:**
`issue-454-p0-p1-p2-remediation-architecture-design-2026-09-26.md`.

## Discovery

The current SVG adapter emits every non-mark primitive in Scene list order and
then emits all mark primitives in a separate terminal `mark-paint` group.  It
sorts only that group by `paintOrder`.  Therefore a Layout-selected text order
would still be overridden by an adapter-local mark layer: an inside label
could be correctly completed above its host yet serialize before every mark.

This is a design/implementation boundary breach, not a localized SVG bug.  A
corresponding target may make a different grouping choice, so merely moving
the axis or label builder loops would preserve the same defect in another
form.

## Corrected decision

Every completed `ScenePrimitive` has a resolved non-negative `paintOrder`.
Layout assigns it from the finite stratum/host relation.  Scene validates and
serializes it unchanged.  Every adapter emits visual primitives in stable
`(paintOrder, Scene input index)` order.  Interaction overlays remain an
explicit post-paint accessibility layer and do not count as visual primitives.

The SVG adapter deletes its mark-only visual group and its mark-specific
ordering branch.  It may retain grouping syntax only when it is observational
(for example, interaction hit areas) and cannot alter visual paint order.
Other adapters receive an equivalent ordering contract and focused target
tests prove it.

## Consequences

- Background bands can reliably paint before axis text regardless of builder
  loop order.
- A hosted text placement receives an order strictly greater than its declared
  mark host; it no longer relies on a later special mark layer.
- Existing mark role order remains Layout/Theme input to mark placement, but
  it is normalized into the same completed primitive order as text and shapes.
- No renderer is permitted to infer a semantic layer from primitive purpose.

## Acceptance addition

Create one mixed Scene fixture containing background, mark, hosted text,
ordinary text, annotation, and a mark interaction.  SVG and each supported
target must preserve the visual primitive order while retaining interaction
semantics.  A source scan/test must reject an adapter branch that reorders by
mark purpose after Scene construction.
