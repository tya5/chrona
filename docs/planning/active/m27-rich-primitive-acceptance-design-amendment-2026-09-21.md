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

## Design completion — R6

The correction is now fully specified by Specification 37. Theme v0.2 grows only two
role binding properties, `fontSize` and `lineHeight`, each referencing an existing
named `number` token. The existing font family and weight bindings remain required;
the Scene stores the four resolved values in `TextLayout`. This preserves current
Theme v0.2 as the sole editable typography resource and prevents a metric or SVG
default from becoming hidden styling authority.

Existing object annotation anchors already identify a projected facet and endpoint.
R6 uses that current contract, resolving it against projected marks, then maps the
result through the completed scale/row geometry. Measured boxes and leaders are
bounded by the `annotations` Layout Manifest slot and its overflow policy. The
existing finite leader router and nearest-port rule supply deterministic geometry;
unsupported, incomplete, or unavailable anchors diagnose rather than degrade.

Dependency marker values remain named Theme marker tokens. The builder records a
selected marker in the completed Path and the SVG adapter emits only the referenced
definition. This does not introduce an SVG-specific marker map or a new authoring
resource.

Implementation is authorized only after the companion R6 review is published. Its
acceptance suite will prove role-specific serialized typography, marker definition and
endpoint attachment, an anchored leader with provenance/bounds, diagnostics for each
missing selection, and materialized output reproduction.
