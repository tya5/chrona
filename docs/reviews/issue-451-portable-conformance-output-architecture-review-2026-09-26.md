# Architecture Review — Portable Conformance Output (#451)

**Decision:** accept.  The runner is the only appropriate transport boundary:
tool contracts remain Unicode and Windows console defaults cannot influence CI
result reporting.
