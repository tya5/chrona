# Issue 145 Network Title-Placement Design Correction

## Trigger and decision

Review immediately before the N145-3B Scene adapter found that N145-3A closes
node-label geometry but not the measured text placement for the network
surface's required `title` slot.  Scene cannot construct that title position
without reintroducing measurement and coordinate ownership at the wrong
boundary.

The network Layout closure therefore includes every required surface text
placement: the single `title` placement as well as one title-label placement
per network node.  This is a correction to the N145-3A completion boundary;
no renderer or use-case change is required.

## Closed input and output

The network composer receives the resolved `title` and `network` slot bounds,
the existing `MeasuredSources` title/network runs, resolved writing mode, and
routing policy.  It creates:

* `TextPlacement("title", ...)` from the measured heading run, placed wholly
  inside the `title` slot; and
* the existing measured `network-label:<object-id>` records, wholly inside
  their node rectangles.

Both placements carry bounds, baseline, lines, typography, and font asset
identity.  A required title that cannot fit emits a stable Layout overflow
diagnostic before Scene.  Scene may map it through the pre-existing
`titleText` semantic, but cannot alter its geometry.

## Boundary review and acceptance

* Layout remains the only owner of title and network label geometry.
* Scene adapter input is the complete placement closure plus registry
  semantics; it has no font metrics or text-placement import.
* Focused tests prove title source/slot absence and title overflow fail before
  Scene, while existing table/timeline title bytes remain unchanged.
* The N145-3B HALCYON gate may start only after this correction is published,
  implemented, independently verified, and merged.
