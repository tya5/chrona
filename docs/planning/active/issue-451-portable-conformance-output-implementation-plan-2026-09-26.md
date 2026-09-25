# Implementation Plan — Portable Conformance Output (#451)

1. Add a small stdout UTF-8 configuration seam to the runner main path.
2. Test that the seam requests UTF-8 without changing rendered content.
3. Run focused runner/tool tests and one three-platform CI release gate.
