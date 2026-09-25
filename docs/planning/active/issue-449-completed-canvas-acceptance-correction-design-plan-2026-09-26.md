# Design Plan — Completed-Canvas Acceptance Correction (#449)

## Trigger

The three-platform run at `c55ff887` reports seven failures of
`test_no_text_leaves_the_viewport` for Controller-Z.  The generated SVGs have
already grown their root canvas beyond the Context request, as required by the
#449 visible-fit policy.  The test still compares text to the requested Context
viewport and therefore rejects the completed artifact it is meant to accept.

## Question

What is the authoritative boundary for an output-property test after Layout
has completed an expanded canvas, and how can the test retain a meaningful
minimum-allocation assertion without reintroducing renderer-local geometry?

## Investigation and decision work

1. Verify the generated SVG root dimensions and `viewBox` against the Context
   viewport for each failing case, and identify whether any emitted text really
   escapes the serialized canvas.
2. Reconcile the acceptance test with #449's completed-canvas contract and
   Specification 50's output-property role.
3. Define one serialized-canvas reader with validation for numeric dimensions,
   origin, and root/viewBox agreement; do not make the test infer canvas size
   from arbitrary child primitives.
4. Review ownership: Layout completes the canvas, Scene transports it, SVG
   serializes it, and the output-property test verifies the serialized result.
   No test-side layout or adapter policy is permitted.

## Planned evidence

- focused tests for a requested-size canvas, a valid expanded canvas, and an
  incoherent root-canvas serialization;
- the complete output-property suite, public materializer reproduction, and
  generated SVG inspection for the formerly failing Controller-Z contexts;
- a three-platform CI run after the correction is published.
