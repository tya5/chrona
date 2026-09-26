# Architecture Review — Surface-Aware Contrast (#459)

Reviewed against Specifications 08, 34, 46, 49, the #431 design and release
review, semantic registry, paint analysis, Scene serialization, and public
HALCYON Scene evidence at `39426438`.

The prior canvas-ground rule is contradicted by completed opaque raised-panel
and band Rects. The selected ground analysis consumes only Scene facts and
preserves Theme/Layout/Scene/adapter ownership. A fixed mark class closes the
coverage gap without classifying arbitrary decorative shapes. Required
`variance-behind` reverses the incorrect de-emphasis of a critical value.

Decision: design accepted for implementation planning. Risks to verify in
code are ground coverage at a centre point, mark forms with stroke-only paint,
and whether every affected light Theme/Scheme can satisfy the floors without
making unrelated state text or marks worse. The public SVG inspection remains
required because Scene evidence alone cannot prove adapter fill behavior.
