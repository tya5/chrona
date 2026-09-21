# Issue #38 reproducibility design review

The materializer, rather than a hand-maintained example context, is the correct owner of immutable closure derivation. It knows the exact source bytes it copies and can make strict CLI identity verification mandatory. Per-slide context selection remains manifest policy; the renderer stays unaware of example and slide identifiers.

Approved for implementation.