# Architecture Review — Completed Paint-Order Adapter Correction (#439)

**Design reviewed:**
`issue-454-p0-paint-order-adapter-correction-2026-09-26.md`.
**Decision:** accepted; required before P0 implementation.

The correction is necessary.  A renderer-side mark layer is a hidden paint
policy and contradicts the established Layout → Scene → adapter authority
chain.  Sorting all visual primitives by supplied `(paintOrder, input index)`
keeps deterministic tie-breaking without assigning semantic meaning to list
position or target-specific purpose groups.

The interaction layer is appropriately excluded: it is non-visual hit-testing
metadata emitted after paint and cannot occlude an artifact.  The implementation
must prove that it remains excluded and that all visual primitive kinds,
including icons and paths, participate in the same order.

No Scene schema compatibility reader is warranted.  Current Scenes with
omitted order normalize to their typed default within the current contract;
the P0 corpus regenerates atomically with its explicit Layout-assigned orders.
