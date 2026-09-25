# Mark composition Scene order and version correction (#398, #396, #397, #399)

## Trigger

The mark-composition design correctly makes paint order independent from source
order, but its statement that an SVG adapter can retain semantic DOM order while
painting ordinary SVG primitives in a different order was incomplete. SVG
paints sibling graphics in DOM order. Continuing without resolving that fact
would either make `markPaintOrder` ineffective or silently change keyboard and
reading order for linked marks.

## Corrected decision

`SceneSurface.primitives` remains the canonical source/semantic order and each
mark primitive carries its completed `paintOrder`. The SVG adapter projects
painted mark graphics into an `aria-hidden` paint layer sorted by that order.
For a mark with a link, it projects a transparent, geometry-identical
interaction rectangle into a source-ordered semantic layer. The interaction
layer carries the completed href, title, purpose and role; it does not measure,
route, select a host, or derive any bounds. Non-mark text remains in canonical
source order and is rendered once.

Thus SVG’s visual stacking and its linked-item traversal order are both
explicit outputs of completed Scene data. This is an adapter projection rule,
not a second layout engine. Adapters without a separate semantic layer must
declare that limitation rather than reinterpret source order.

## Scene contract

Scene v0.3 supersedes v0.2. It adds authoritative primitive fields:

* `paintOrder` — completed numeric visual stacking order;
* `clipSourceId` — a completed reference to the host outline for a fill; and
* `endTreatment` — `closed` or `open`, selected by Layout.

The Scene validator verifies that a clip source exists, precedes its dependent
fill in canonical source order, is a compatible mark outline (closed or open),
and is in the same slot. An open actual remains a completed host outline and
may therefore contain its own progress fill; its terminal treatment does not
make the observed extent incomplete. SVG creates a clip definition only from that validated source;
an adapter must not recreate rounded geometry or infer an open end.

## Lane geometry clarification

`timeline.mark.blockSize` is the base extent of one lane slot. A row may have
additional spare space for labels or allocation, but role ratios are evaluated
only inside that fixed slot. Stacked lanes consume one base extent each;
shared lanes intentionally share it. This preserves a mark’s physical size
when the viewport makes its row taller and makes `E_LAYOUT_MARK_OVERFLOW`
about actual lane containment rather than incidental row height.

## Architecture review

The correction keeps temporal facts in Project/Actual, policy in View/Theme,
all geometry and host selection in Layout, and completed geometry in Scene.
The SVG adapter only serializes two representations of those completed Scene
primitives. It therefore preserves the architecture boundaries established by
Specification 32 and Specification 50, while making accessibility and visual
order independently testable.
