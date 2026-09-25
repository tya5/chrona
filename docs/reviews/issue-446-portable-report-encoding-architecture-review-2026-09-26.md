# Architecture Review — Portable Scene Report Encoding (#446)

**Decision:** accept.  Encoding belongs at the CLI/tool transport edge, not in
the evaluator, Scene model, Layout, or a renderer.  Explicit UTF-8 preserves
the serialized-Scene contract and #451's cross-platform reporting boundary.
