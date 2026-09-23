# #345 Portable Visual Capabilities Architecture Review

**Decision:** Accepted for the v0.6 initial scope

The design preserves the Layout -> Scene -> adapter direction. Theme/Scheme
remain the only appearance authority; Scene carries bounded completed values;
adapters only serialize/reject them. Existing semantic/source/accessibility
metadata persists independently of decoration. SVG is an implementation target,
not an input language.

Image and path clip require asset closure and geometry/cross-target work; richer
gradients/effects require demonstrated capability profiles. They are explicitly
deferred, not represented as generic values. This keeps a future Canvas/PPTX
adapter honest while providing a current SVG/PNG/PDF capability profile.
