# #42 slide-grade vocabulary 設計レビュー（2026-09-21）

承認。

- overlay is a ReviewRow composition property, not an Actual exception.
- group headers are View-derived Scene structure with Theme internal geometry, avoiding a Project presentation field.
- axis formatting reuses the current axis algorithm; as-of is emitted only from declared Actual cutoff.
- legend schema correction belongs to Detail Profile, while swatch geometry belongs to Scene/Theme.
- mark labels and callout rail reuse #41 behavior.
- all additions preserve immutable closure, renderer-neutral primitive contracts, and removed Settings/legacy Theme boundaries.
