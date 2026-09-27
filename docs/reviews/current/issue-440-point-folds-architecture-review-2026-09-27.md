# Architecture Review — Milestone-Only Rows and Fold Policies (#440)

**Decision:** design approved. Implementation is sequenced after #467 L3. **Reviewed:** [#440 design](../../design/issue-440-point-folds-design-2026-09-27.md).

| Boundary | Result |
| --- | --- |
| Projection | `key-row`, fallback lists and fold membership are row composition, as are the existing folds. |
| Layout | Group-header and key-row packing call #467's `allocate_lanes`. There is one allocator and one label ladder. |
| Labels | A folded point's label reuses #486's required composition, so names never depend on an optional label policy. |
| View schema | `key-row`, `keyRow.title`, a list form of `points` and `pointsReason` take the next free View version, shared with #479 and #486. |
| Tooling | The 25% bound is a corpus report check, not a render rule, so user projects are unaffected. |

**Risk:** the key row adds a synthetic table row. It carries only its title, and its cells are empty by design, not missing.
