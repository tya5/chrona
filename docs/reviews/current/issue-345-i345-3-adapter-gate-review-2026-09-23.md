# #345 I345-3 Adapter and Fidelity-Gate Review

**Decision:** accepted.

The render use case resolves and validates the Context profile before choosing a
renderer, completes optional omission in Scene, and rejects unsupported required
treatment before serialization.  SVG serializes deterministic IDs derived from
completed values, normalized object-bounding-box linear gradients, one
`feDropShadow`, and closed line finishing.  PNG and PDF consume that same SVG
route; their rich-scene characterization confirms deterministic valid bytes.

Renderer modules have no Theme, Scheme, Scene resolver, or visual-profile-policy
dependency.  Typst/TikZ cannot select the rich profile and therefore reject it
at the use-case gate instead of receiving unrepresentable completed values.
