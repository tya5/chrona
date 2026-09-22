# Issue 125 Placement-decision Design Correction

## Trigger

The first implementation pass put a label's requested ladder and chosen side
on `TextPlacement`, while the approved design called that record a
`LayoutManifest` entry.  That is an architectural mismatch: the manifest is
the early slot-allocation input to Layout, whereas feasibility is known only
after marks, measured text, obstacles, and annotation boxes have been
composed.  Recording a late decision in the manifest would either make that
input mutable or force Scene to recreate Layout work.

The same inspection showed that accepting `relations` and `annotations`
fallback syntax without a complete candidate vocabulary would publish a
non-operative contract.  A relation route and an annotation box use different
feasibility algorithms and cannot share unnamed string rungs.

## Corrected contract

Issue 125 provides one bounded, operational placement-preference capability:

* `presentation.label.side` on a View row or item, and
  `visibility.fallback.labels`, govern plot-label candidates.  An item intent
  prepends its preferred side and retains the remaining View ladder in order.
* `presentation.callout.placement` on a View row or item governs a callout
  anchored to that selected row/item.  Its candidate vocabulary is
  `above`, `below`, `start`, `end`, and `rail`; an annotation-specific View
  fallback uses exactly that vocabulary plus optional terminal `suppress`.
* `presentation.text.wrap` applies to the label or callout text emitted for
  that subject.  `allow` permits the Layout-owned deterministic line-break
  search within the candidate bounds; `forbid` retains one measured line.
  It does not silently change table-row allocation.  Table wrapping needs the
  independent measured-minima/row-height policy and remains outside this
  issue.

The schema must reject empty ladders, duplicate rungs, `suppress` before the
last rung, and a ladder with no feasible candidate before `suppress`.  The
existing relation visibility remains an overflow policy; no relation fallback
array is exposed in v0.4.  A future routing-preference design must define
route candidate semantics (ports, lanes, and obstacle policy) before adding
such a field.

## Decision evidence and ownership

`SurfacePlacement`, the completed typed Layout closure, owns an immutable
`PlacementDecision` sequence.  Each decision records its stable identity,
source reference, requested ladder, selected rung, and outcome
(`placed`, `suppressed`, or `diagnosed`).  The decision refers to the matching
text, shape, or relation placement but does not itself carry renderer data.
This gives annotations a single decision even when they emit a box, text, and
leader.  It also avoids overloading early `LayoutManifest` allocation data.

View parsing retains author intent.  Projection carries it only with the
selected row/item occurrence.  Normalization resolves the annotation anchor's
selected occurrence and passes the resulting intent to Layout.  Layout alone
measures, wraps, tries candidate geometry, routes leaders, and records the
outcome.  Scene receives only completed placements and decision evidence; it
does not inspect intent or retry a rung.

## Architecture consistency review

The correction preserves the established boundary:

```
Project facts + View intent -> normalized closure -> Layout decisions/geometry
                                  -> Scene primitive projection -> renderer
```

Project remains the owner of annotation facts and anchors; View controls only
their presentation preference for a selected occurrence.  Layout keeps every
geometry and typography decision.  The Scene and renderer stay independent of
fallback semantics.  The closed semantic registry remains unchanged, in line
with the previously published presentation-extension correction.

## Superseded statements

The Issue 125 design's phrase “typed Layout manifest” is replaced by “typed
completed Layout placement closure.”  Its generic relation/annotation ladder
claim is superseded by the explicit label and callout vocabularies above.
Package-defined presentation extensions remain deferred under the correction
published in PR #207.
