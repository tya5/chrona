# M27 Rich Primitive Acceptance Design Amendment — 2026-09-21

**Status:** M27 completion is reopened; I27-R6 is required before issue closure.

Final issue review found that the current v0.5 path does not yet meet all acceptance
criteria claimed by #29/#33. In particular, it lacks declared per-role typography,
annotation leaders anchored to projected objects, and declared marker serialization
for routed dependencies. M27 therefore remains in progress; the existing materializer
proves reproducibility of the current output but does not prove this richer vocabulary.

I27-R6 must add only generic current-resource mechanisms: Theme v0.2 role typography
bindings, bounded annotation anchor/leader construction, and marker token use by the
v0.5 SVG adapter. Each selected family must be source-provenanced, bounded by the
Layout Manifest, and covered by materialized-example acceptance. No legacy paint map,
Settings object, example branch, or arbitrary coordinates may be introduced.
