# Design Correction: Annotation Rail Target Closure (#350)

**Status:** Design complete — amends I350R-4 before annotation and note-index visual acceptance.

## Finding

The v0.12 View schema admits `annotation` and `note-index` visual targets and
Layout already owns their candidate-box and leader-route composition.  No
published reusable table-timeline Layout, however, declares an `annotations`
source region.  The targets therefore lack public authoring evidence and a
stable region through which a View-local callout can be materialized.

## Corrected contract

Controller Z's shared executive Layout gains one optional `annotations` source
with a declared rail extent in its footer flow.  This is an annotation rail, not a View coordinate system:
the slot supplies only a bounded Layout region.  A View annotation continues
to own its stable ID, typed selected-object anchor, purpose, and logical
placement/fallback.  Layout computes the callout box, pre-reserves any visual
advance, selects its candidate, and routes the leader.  Scene projects the
completed box, text, note index, icon, and leader.

The source is optional because a shared Layout must support Views with no
visible annotations.  When an annotation is visible, its source is required
by the normal complete-or-absent composition path; it is never silently
dropped because a renderer lacks a rail.

## Architecture consistency review

This uses the existing authority chain without adding a presentation-side
coordinate or fallback seam: Project/View provide facts and intent, Layout
owns geometry and routing, Scene carries only completed primitives, and the
SVG adapter serializes them.  Placing the rail in the existing footer preserves
the timeline/table allocation while giving Layout a declared non-mark obstacle
region for annotation fitting.

## Acceptance

- a View-local numbered callout with leading annotation and note-index visuals
  materializes through the shared Controller Z Layout;
- the emitted icon, callout text, numeric index, box, and leader retain stable
  provenance and are all completed before Scene;
- absent annotations leave public Controller Z materializations byte-stable;
- no Scene code measures annotation text, selects a callout candidate, or
  routes the leader.
