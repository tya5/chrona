# Implementation Plan: mark composition (#398, #396, #397, #399)

## B1 — Contract and typed placement foundation (#398)

Add v0.8 Theme, v0.3 Actual Set, and v0.14 View contracts; update inventory
and consumers atomically. Extend typed placement/Scene serialization with
semantic role, paint order, clip-host identity and end treatment. Add schema,
contract and invalid-geometry tests.

**Acceptance:** no active source uses fixed mark height/offset/order/radius
literals; role geometry derives track minimum and validates overflow.

## B2 — Layout composition (#398, #399)

Resolve per-role lane geometry in `place_mark_tracks` and surface composition.
Project and preserve `openUntil: asOf`; emit a warning and no mark when as-of
is unavailable. Keep open actual distinct from finish and missing observation.

**Acceptance:** a nested actual exposes independent dates; open actual hosts
progress; missingActual occurs only for absent actual data.

## B3 — Badge and contained progress (#396, #397)

Resolve mark-icon bounds and independent `iconMark` paint in Layout/Scene.
Attach partial progress placement to its host clip; implement typed Scene/SVG
clip delivery and open-end treatment with no adapter inference.

**Acceptance:** icon badge is legible; rounded partial progress is contained
with square trailing edge; serializer tests reject invalid clip references.

Before B3 implementation, apply the published Scene order and version
correction: Scene v0.3 carries completed paint/clip/end fields, and SVG uses
separate visual paint and source-ordered linked-interaction projections rather
than relying on impossible independent sibling DOM z-order.

## B4 — Corpus and release gate

Add one slide (or tightly scoped declared variants) exercising: a container
baseline plus nested actual, contrasting circle-host icon badge, rounded partial
progress, open actual to as-of, late start and overrun. Regenerate all affected
Scene/SVG evidence through the public materializer and refresh coverage.

Run focused tests, conformance, structural gates, public materializer bytes,
generated-SVG visual review, full parallel pytest, wheel smoke and CI. Publish
an acceptance review before closing #398, #396, #397 and #399.
