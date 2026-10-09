# Declared Colour Scales

**Status:** Accepted
**Depends on:** [06 View Model](06-view-model.md), [07 Style and Theme](07-style-and-theme.md), [08 Scene and Rendering](08-scene-and-rendering.md), [34 Color Scheme Authoring](34-color-scheme-authoring.md), [49 Semantic Presentation Contract](49-semantic-presentation-contract.md)
**Owns:** the closed, data-dependent colour-encoding contract and derived scale legend.

## 1. Boundary

A declared colour scale is a total, reviewable mapping from one declared
source-domain value to one concrete Scheme colour. It is not an ordered rule
engine, a predicate language, a per-object literal, or a renderer callback.
The three owners remain separate:

| Owner | Declares |
| --- | --- |
| View | eligible target, field source or closed derived interval key, scale ID, and ordered domain |
| Theme | exact mapping from each scale-domain value to a named Scheme category slot |
| Color Scheme | named category slot to `#RRGGBB` literal |

For mark encodings, the View's tagged source is `{field: <declared Project field>}`; strings are
never interpreted as either fields or colours.  An encoding may target only a
standard mark semantic role declared eligible by this version.  The initial
eligible role is `planned` member marks.  A scale domain is non-empty, unique,
and ordered solely for stable legend reading order; no paint choice depends on
position.

## 2. Total mapping and diagnostics

For every View domain value, Theme must provide exactly one mapping to a Scheme
slot, and the Scheme must provide that slot.  The mapping keys must exactly
equal the View domain.  At evaluation, every selected eligible object must
have a scalar source value in that domain.  Missing, non-scalar, or undeclared
values reject the presentation closure with `E_PRESENTATION_SCALE_VALUE`,
including the object ID, field, and value state.  Missing Theme mappings or
Scheme slots reject closure with `E_PRESENTATION_SCALE_MAPPING`.

An ordinary Theme colour binding may also explicitly name one category slot for
a static role (for example a group band).  That is a direct role-to-slot
binding, not a scale: it has no field source, domain, or derived legend.

There is no hash selection, positional range matching, palette recycling,
default grey, inherited role colour, or renderer fallback.  Changing a Scheme
literal may repaint an output; changing a View domain or Theme mapping changes
the evaluated presentation closure explicitly.

## 3. Evaluation and Scene boundary

Closure validation resolves the typed scale table from the pinned View, Theme,
and Scheme. Projection supplies selected field values; axis encodings use the
neutral temporal source of section 7 instead. Semantic projection
first establishes each standard mark role; appearance completion then looks up
the resolved scale value for an eligible primitive's source object and replaces
only that paint channel.  Layout never reads a Scheme or field value, and Scene
does not parse an encoding, choose an unknown policy, or calculate geometry.
Adapters receive completed concrete paint and cannot re-evaluate a scale.

## 4. Derived legend

A scale legend is derived from the selected values that actually occur on
eligible marks, in declared domain order.  Each entry has the domain value as
its label, the corresponding completed colour, and stable scale/value
provenance.  Layout places the resulting entries; Scene emits their completed
swatches and text.  A manually authored entry cannot duplicate or override a
scale-derived entry for the same scale.  Existing semantic legends retain their
separate role/label ownership and may coexist; they do not claim to enumerate
the scale domain.

## 5. Migration boundary

This is an atomic replacement of the current category mechanism.  The next
resource revisions replace the Scheme `category` array with a named category
slot map, replace generic `category` Theme bindings with explicit named-slot
bindings, and add scale-derived entries alongside existing semantic legend
entries.  All shipped Contexts and generated evidence migrate in the same
change.  No v0.1/v0.3 compatibility reader, hash-category fallback, or
partially materializable resource set is retained.

## 5.1 Domain separability (#421)

Scale resolution compares every pair of resolved domain colours with
CIEDE2000 on sRGB. The comparison is made under normal vision, and under each
deficiency the Color Scheme claims in `suitability.colorVision`, simulated
with the Machado, Oliveira and Fernandes (2009) matrices at severity 1.0;
`none-claimed` adds no simulated vision. A pair below
`MINIMUM_CATEGORY_DELTA_E = 5.0`, including an exact duplicate, is a
non-fatal `W_PRESENTATION_SCALE_NOT_SEPARABLE` naming the scale, both values,
the vision and the difference. It is reported in the CLI and as the Scene
diagnostic `W_PRESENTATION_SCALE_NOT_SEPARABLE:<scale>:<first>:<second>:<vision>`.
Rendering continues. Committed evidence carries no such diagnostic.

## 6. Non-goals

Multiple simultaneous encodings, predicates, ranges, continuous scales,
per-object literals, rule ordering, conditional style, and progress/disposition
paint are outside this contract.  Progress fill remains a distinct mark
vocabulary decision.

A per-group band tint (View `grouping.tint`, [Specification 50](50-constraint-driven-gantt-surface-quality.md)
section 3.4) is a second, separately named scale over the grouping field's
values. It reuses sections 2, 3 and 5.1 unchanged and does not widen the
single mark encoding above.

## 7. Axis-band interval scales (#490)

A fixed-unit View band tier may opt into `fillScale: {scale, key, containingTier?}`.
`key: alternating` uses the complete ordered domain `["0", "1"]`, selecting the
natural interval ordinal modulo two. `key: interval` uses decimal-string ordinals
of all retained intervals of the selected source tier. Ordinals start at zero for
the first natural bucket intersecting the View window; clipping and `every` never
renumber retained buckets. They are not labels, dates or Project fields.

`containingTier` may name any declared, strictly coarser fixed-unit band tier,
including one declared later. Each child's full natural interval must have exactly
one retained parent container; window clipping does not create containment. Gaps,
crossing intervals, self/finer/labels/auto parents refuse with
`E_PRESENTATION_AXIS_SCALE_PARENT` at the tier's `fillScale/containingTier`.

Theme supplies an exact `slots` mapping for the whole source domain, even unused
parent values; palettes and missing/extra keys are `E_PRESENTATION_SCALE_MAPPING`.
Section 5.1 checks distinct domain entries, not repeated physical band cells.
The opted-in band role must be drawable with `backgroundTreatment: fill` and no
covering gradient; otherwise `E_PRESENTATION_AXIS_SCALE_TARGET` identifies the
View tier. Existing opacity, pattern ink, borders and paint order are retained.
There is no axis-scale-derived legend or implicit fallback.

Presentation resolves finite temporal values from the same neutral interval
function/window/fiscal inputs as Layout, completing Scheme colours keyed by
canonical band placement identity. Layout still owns interval geometry and text.
Scene only attaches those passive colours to completed primitives; adapters
neither select an interval nor evaluate a scale. Omission preserves existing output.
