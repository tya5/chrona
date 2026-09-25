# Mark composition design (#398, #396, #397, #399)

## Decision

Marks are independently meaningful, completed Layout placements.  A role's
lane-relative geometry determines its bounds; optional compositions then name
an already-completed host placement.  This replaces fixed comparison-track
literals with explicit Theme treatment, without turning Scene or an adapter
into a layout engine.

## Contracts

Theme v0.8 supersedes v0.7.  A mark-capable semantic role may bind named
numeric tokens for `markHeight`, `markOffset`, and `markPaintOrder`; height and
offset are non-negative ratios of the assigned lane-slot extent, and paint
order is an integer. `cornerRadius` remains a completed role treatment rather
than a primitive-shape literal. `iconScale` on `iconMark` means a host-mark
height ratio; labelVisual retains its typography-relative meaning because each
binding identifies the coordinate context.

Actual set v0.3 supersedes v0.2. An observation span may state
`openUntil: asOf`; it is legal only with `start`, never with `finish`, and
means an observed open span rather than a manufactured finish. An absent set
`asOf` is a named Layout warning and produces no actual placement.

View v0.14 supersedes v0.13 only where necessary to preserve the closed
progress-host selector and role geometry ingress. Existing `progressFill`
remains a fraction applied to its selected completed mark; it never expresses
one time span nested inside another.

## Placement model

`MarkPlacement` gains its resolved semantic id, paint order, and end treatment
(`closed` or `open`). Layout derives each mark bounds from its assigned stack
slot, using the source role's height/offset. The minimum track extent is the
maximum `offset + height` of the roles actually placed in that slot. Invalid
or overflowing geometry raises `E_LAYOUT_MARK_OVERFLOW` with role, offset and
extent provenance.

Paint order is separate from primitive/source order: Scene preserves stable
source order for semantics and accessibility, and exposes a completed numeric
paint order. Render adapters draw by that order while retaining semantic DOM
order. Thus author treatment cannot silently change reading order.

A `ShapePlacement` may name `clip_host_id`. Layout may set it only to a
non-suppressed completed `MarkPlacement` in the same slot. Scene preserves a
typed clip reference; SVG defines the host outline once and applies it to the
fill. The fill itself stays a rectangle, so a partial fill has a square
trailing edge and the host clip supplies only its leading containment.

An icon visual targeted at a mark is a badge: the host stays visible, and the
icon uses `iconMark`'s independent contrasting paint role. Layout centers an
inset rectangle calculated from the completed host bounds. It cannot replace,
resize, or select the host in an adapter.

`openUntil: asOf` resolves in projection as an `actual_open` span retaining
the declaration. Layout alone replaces its right coordinate with the actual
set's declared as-of. The end treatment is open (a completed Layout/Scene
shape treatment), while `finish` produces closed. `missingActual` is emitted
only when the projection has no observation.

## Architecture review

Project/Actual retain temporal facts; View selects presentation; Theme supplies
role treatment; Layout resolves all geometry and containment; Scene carries
only completed geometry; adapters serialize it. This satisfies Specification
32 and prevents the three common boundary failures: renderer clipping
inference, Scene placement decisions, and fabricated actual finish facts.
It also respects Specification 50: clipping and icon insets are selected
before Scene, and overflow remains a Layout diagnostic. Stable semantic order
preserves the accessibility contract while explicit paint order permits visual
nesting.

## Consequences

* A taller baseline container and a shorter actual may share a lane and still
  expose late starts/overruns as independent date ranges.
* Rounded partial progress becomes mechanically contained rather than relying
  on a matching fill radius.
* Mark icon corpus evidence can realize `icon-mark`; rounded/progress and open
  actual evidence must be materialized in the same release.
* No compatibility shim is retained for v0.7/v0.2/v0.13 as live contracts.
