# #41 実装計画（2026-09-21）

1. Add `timeline.mark.blockSize` to Theme measurement requirements and example themes.
2. In the Scene builder, use fixed mark size, emit explicit-member labels when View labels are visible, and retain concrete per-mark ports.
3. Give snapshot marks the `snapshot` visual role and require the resolved Theme binding.
4. Route same-row relations from distinct ports and reject unavailable paths before SVG serialization.
5. Implement annotation-rail placement using the annotations slot; add focused regression tests for labels, size invariance, same-row relations, snapshot color role, and required/optional callouts.
6. Publish implementation review; pytest execution remains delegated as directed.
