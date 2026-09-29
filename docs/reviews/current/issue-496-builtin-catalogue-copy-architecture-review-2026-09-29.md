# #496 builtin catalogue copy architecture review

**Decision:** approve the [Slice 3 design amendment](../../design/issue-496-builtin-catalogue-copy-design-amendment-2026-09-29.md) and its implementation-plan amendment. **Base:** current #496 design and approved density, pattern-admission, and note-host corrections; issue #496 remains open with no later comments.

The library's explicit v0.2 references fit the existing wheel-owned preset catalogue and keep package identity separate from runtime resource identity. `presentation-preset/v0.1` already pins catalogues and detail profiles; preserving it avoids a duplicate closure schema. Copy carries exact catalogue and notice bytes and preserves those references, while the render path resolves the same finite closure. This is consistent with Spec 64 licensing/identity, Spec 07 Theme selection, Spec 08 completed Scene/adapters, and #479 detail-profile ownership.

The layer boundary remains intact: library data declares members, import owns normalization/provenance, Theme binds assets, closure verifies them, Layout completes geometry, Scene carries completed values, and adapters serialize them. No preset or adapter discovers assets. The generic bundle may demonstrate a glyph and pattern on an admitted role, but must not put a pattern on the #466 note host. The pattern's substrate/ink and density semantics remain those already reviewed in Specs 07/64 and the #496 corrections.

Spec 62 stays proposed and is not a dependency for this wheel-only path. Updating its description of the implemented predecessor to library v0.2 clarifies the future resolver's migration boundary; it grants no package acquisition behavior. No domain facts, new theme vocabulary, Context fields, or asset kinds are introduced.

**Gate:** implementation must establish packaged resource identity, complete notices, exact copied references, error behavior, and public `render --preset` evidence. Actual copied output and SVG/decoded PNG remain required for the two literal acceptance criteria; this review does not mark them met.
