# Axis Thinning Record Design Amendment (#405, #406, #407, #408, #400)

**Status:** Accepted before atomic I2/I3 implementation.

`thin-with-record` is a deterministic Layout policy over the completed,
ordered label interval outcomes of one selected axis tier.  It never changes
calendar buckets, label text, the View's declared `every`, or Scene geometry.

For a tier whose measured labels do not all fit, Layout chooses the smallest
positive thinning stride for which one non-empty periodic phase retains only
fitting candidates.  Among phases for that stride it chooses the smallest
zero-based phase.  The period is over the ordered candidate sequence after the
View's declared `every` has been applied.  This makes the result independent
of host locale, renderer, hash-map iteration, and incidental placement order.

Each candidate interval has one completed disposition:

* `placed` when retained and emitted as a text placement;
* `thinned` when omitted by the selected schedule or because it cannot fit.

For every `thinned` candidate, Layout emits a stable
`W_LAYOUT_AXIS_LABEL_THINNED:<candidate-id>:<reason>` diagnostic.  Reasons are
`label-does-not-fit` and `thinning-stride`.  Layout also emits one
`W_LAYOUT_AXIS_DENSITY` diagnostic with the selected tier, stride, and phase.
Those diagnostics are carried through the Scene serialization; no renderer
infers them.  They are the required evidence that a reader cannot recover from
the picture alone.

Under `diagnose`, any non-fitting candidate remains
`E_PRESENTATION_AXIS_OVERFLOW`; it is never converted to thinning.  If no
fitting periodic schedule exists, `thin-with-record` also diagnoses.  This
keeps declared policy meaningful and excludes silent deletion.
