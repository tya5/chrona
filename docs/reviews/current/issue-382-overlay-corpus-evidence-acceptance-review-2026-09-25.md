# Acceptance Review: Overlay corpus evidence (#382)

**Decision:** Accepted, pending final three-platform CI.

## Delivered boundary

HALCYON now contains the reproducible `overlay-briefing` Context closure and
its public SVG and Scene evidence.  Its current v0.4 Layout has an `overlay`
root, the named `review-top` block guide, two inline barriers, and anchored
title, table, timeline-axis, and timeline placements.  The wallboard Theme
owns `panel.review.block`; the overlay Layout consumes that semantic token
instead of embedding a review-height constant.

The final scope deliberately keeps the sidebar title-only.  Optional summary,
notes, and legend content remain owned by the existing wallboard Layout rather
than inventing a detail-rail policy while proving overlay composition.  At the
2560 by 1560 evidence viewport, the solver places title/table/timeline-axis at
block coordinate 225, places the table at inline coordinate 484, and leaves a
914-pixel timeline body beneath the 46-pixel axis.  The focused materializer
test asserts those guide, barrier, gap, and bounded-review facts.

The new theme token changes only the immutable provenance identity of the four
existing HALCYON Scene artifacts that use that Theme.  They were regenerated
through the public materializer.  Their SVG bytes are unchanged.  The new
artifact and the regenerated presentation-coverage report establish real
evidence for live overlay, guide, barrier, and anchor vocabulary.  The gallery
deferred entry now correctly names the remaining work: a deliberately
composable responsive View/Layout comparison, not basic overlay grammar.

## Design and architecture review

The published height-token and required-sidebar corrections were completed
before implementation.  The resulting ownership remains aligned with the
whole architecture: Theme supplies reusable constants, View declares review
intent, Layout allocates geometry, Scene projects completed placements, and
the public materializer provides byte evidence.  No compatibility syntax,
responsive policy, SVG parsing, or new gallery pair was introduced.

PRs #272 and #283 were closed without merge as required; their proposed
history is not an implementation source for this evidence.

## Verification

| Gate | Result |
| --- | --- |
| Overlay focused materializer and coverage tests | Pass |
| Declared public corpus materialization | Pass, 21 slides |
| Generated coverage, gallery, corpus, diagnostics, and vocabulary checks | Pass; no stale generated output |
| Conformance and structural checks | Pass; 75 reachable modules, 32 delivered Scene fields, 10 View values, 9 inward-only packages |
| Full suite | `769 passed, 19 skipped` |
| Wheel | 2,506,550 bytes, below 5,000,000-byte limit; isolated installed-wheel smoke passed |

The full-suite warnings are the existing `jsonschema.RefResolver` deprecation
warnings.  Issue closure requires the CI run for this acceptance commit to
pass on Ubuntu, macOS, and Windows.
