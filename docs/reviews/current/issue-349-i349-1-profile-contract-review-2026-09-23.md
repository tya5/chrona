# #349 I349-1 Exact Profile Contract Review

**Decision:** accepted.

The generic v0.6 profile has been replaced by exact `v0.6-svg` and `v0.6-png`
identifiers. PDF, Typst, and TikZ retain only baseline admission, so an SVG
effect can no longer be silently inherited by PDF. The Controller Z Elevated
Context migrates atomically to the SVG identifier; no generic v0.6 reader
remains.

Explicit and guided draft rendering now accept the same exact profile selector
as immutable Context rendering. The profile resolver is still outside adapters,
and a rejected profile keeps its diagnostic message and target-property pointer
through the render use case and CLI boundary. Theme fidelity bindings are now
treatment-specific. Focused Scene/profile/materializer checks passed (`19
passed`).
