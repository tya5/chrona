# Design Plan: Overlay corpus evidence (#382)

**Status:** Accepted.

## Verified starting point

* #272 and #283 are closed without merge; their branches are not an
  implementation base.
* `chrona/layout-profile/v0.4` is the one live Layout Profile contract.
  It supports overlay containers, guides, anchors, and barriers; the Layout
  resolver and engine already validate and solve them.
* The 20-slide corpus has no declared use of overlay, guides, anchors, or
  barriers.  The published presentation coverage report confirms this.
* #375 is closed with current v0.2 Scene evidence, so #382 can use that report
  as its acceptance reader.

## Design questions

1. Which existing corpus project and current resources provide the smallest
   honest surface for a responsive overlay composition, without reviving #272's
   obsolete contracts or hand-authoring render evidence?
2. Can one current Layout Profile use an overlay root, guide-targeted anchor,
   and barrier-targeted anchor while retaining required table/timeline
   materializability and deterministic routing?
3. What observable Geometry/Scene assertions distinguish guide and barrier
   resolution from merely declaring their YAML keys?
4. Does the new composition unblock #354's `programme-at-scale` deferred
   gallery set?  If not, what precise blocker remains?

## Required outputs

* An English design, architecture-alignment review, and implementation plan.
* One declared regression-corpus slide with current Context closure, generated
  SVG and Scene evidence produced solely through the public materializer, and
  semantic tests of overlay, guide, anchor, and barrier resolution.
* Regenerated coverage and gallery artifacts, including an explicit update to
  the `programme-at-scale` deferred disposition.

## Guardrails

* Do not copy/rebase #272 assets or retain its obsolete contract versions.
* Do not extend Layout syntax or introduce raw-coordinate authoring merely to
  create an example; #382 exercises the current bounded grammar.
* Do not treat schema declaration as output evidence.  The slide must pass
  public materializer byte checks and expose completed Scene evidence.
