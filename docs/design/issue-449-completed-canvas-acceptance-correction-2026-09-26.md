# Design Correction — Completed Canvas Is the Output Boundary (#449)

**Design plan:** `issue-449-completed-canvas-acceptance-correction-design-plan-2026-09-26.md`  
**Corrects:** the acceptance evidence implied by
`issue-449-visible-fit-failure-policy-design-2026-09-25.md`.

## Finding

The #449 contract deliberately makes a Context viewport a minimum allocation.
Layout may complete a larger `canvas_bounds`; Scene transports that result; an
SVG adapter serializes it as root `width`, `height`, and `viewBox`.  The output
property `test_no_text_leaves_the_viewport` instead reads the requested Context
dimensions and calls those the canvas.  It consequently reports text in a
valid completed footer as outside a 1600 x 900 request even when the serialized
SVG declares a 1600 x 1032.8 canvas.

That is a stale acceptance boundary, not a known output failure.  Pinning the
seven failures would institutionalize a contradiction in #449; moving footer
text back inside the requested height would reverse its visible-fit policy.

## Decision

For a serialized SVG output-property test, the root SVG canvas is authoritative
for containment.  The test reads and validates one `SerializedCanvas` from:

```text
<svg width="W" height="H" viewBox="0 0 W H">
```

The reader rejects absent, non-finite, non-positive, or mutually inconsistent
dimensions.  It also requires a zero origin, because Chrona's completed canvas
is anchored at the requested origin.  A text box may not cross that serialized
canvas.  The requested Context viewport remains evidence of the lower bound:

```text
serialized.width  >= requested.inlineSize
serialized.height >= requested.blockSize
```

Thus a serializer cannot conceal a layout escape by shrinking or translating
the root canvas, while a valid Layout expansion is accepted.

## Boundaries

Layout remains the sole owner of completed canvas geometry.  Scene remains a
verbatim carrier, and the SVG adapter remains a serializer.  The acceptance
test neither completes geometry nor reads Scene-internal data: it checks the
published document that users receive.  It must not derive bounds from text,
rectangles, CSS overflow, or an allowlist.

## Acceptance

1. A requested-size SVG and a larger, coherent completed SVG both pass their
   containment checks when their text lies inside their serialized canvas.
2. A root canvas smaller than the request, non-zero-origin viewBox, or root /
   viewBox dimension disagreement fails deterministically.
3. All seven Controller-Z cases use their completed SVG canvas and have no
   text outside it.
4. The correction does not modify Layout, Scene, adapter serialization, or
   Context resource syntax.
