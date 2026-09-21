# M27 I27-R3B1 Optional Normalization Review — 2026-09-21

**Decision:** Complete and published as the first R3B sub-slice.

The v0.5 normalizer consumes current Project/View/projection inputs only. It has no
deleted Settings dependency. Group decoration, finite semantic dependency routes,
legend entries, and Project notes are emitted only when their normalized content and
Layout slots exist. Annotation/detail/summary materialization remains R3B2.

**Evidence:** `test_v05_content.py`, full regression (196 passed), conformance.
