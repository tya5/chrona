# Design Plan — Footer Side-Content Geometry Closure (#455)

**Trigger:** The #446 read-only P0 corpus audit found two completed-Layout
failures: positive-area overlap between adjacent project notes and
`ellipsize-with-source` legend text outside its slot after the swatch.
**Entry condition:** #445 remains limited to measured group-detail and
milestone panels.  This plan must not retroactively enlarge that slice.

## Objective

Complete notes and legend text as ordinary Layout-owned side-content blocks so
their supplied Scene geometry respects the declared slot/overflow contract.
The work must preserve the one-way Intent → Layout → Scene → adapter boundary
and establish a clean P0 baseline before #446 implementation begins.

## Questions to resolve in design

1. What is the smallest shared side-content block abstraction that composes
   sequential notes and legend entries without combining their semantic
   selection, presentation, or Scene projection responsibilities?
2. Which closed visual reservations (legend swatch, label visual, gap) reduce
   the text's available inline interval, and which geometry remains within the
   parent slot versus being an explicitly separate primitive?
3. How does each declared overflow disposition constrain text bounds:
   `ellipsize-with-source` must contain its completed text; `visible-overflow`
   may escape only with a completed warning; `clip-optional` may suppress only
   through its existing completed record?
4. How do completed line height, multiline text, and slot block extent
   determine deterministic note cursor advancement and canvas expansion?
5. Which existing #445 helpers can be reused without treating notes/legend as
   paragraph panels or introducing a generic collision-repair pass?

## Required design and review outputs

- an English design defining data ownership, measured available bounds,
  sequence/spacing rules, slot containment and warning invariants;
- an architecture review against #445, #449, #446, and existing visual
  reservation ownership;
- a separate implementation plan naming source helpers, affected public
  contexts, fixtures, generated artifacts, acceptance criteria, and release
  gates.

## Verification design inputs

- a Controller-Z project-note fixture proves adjacent notes have no
  positive-area overlap while preserving their source order and selected
  typography;
- a HALCYON programme-board fixture proves swatch-reserved legend text is
  ellipsized inside the full legend slot and preserves source content;
- an explicit visible-overflow fixture proves #449’s permitted result remains
  visible, warned, and inside the completed canvas;
- a committed-Scene audit proves no project-note overlap and no
  `ellipsize-with-source` text escape at micro-point tolerance;
- public materializer reproduction, generated diff review, structural
  direction checks, and remote CI are the release evidence.  The local full
  suite is not duplicated.

## Stop conditions

Stop for a new design correction before implementation if the solution needs a
new View/Profile syntax, a Scene-specific layout decision, adapter clipping,
or changes the meaning of #449 visible overflow.  Do not encode current
corpus findings as #446 allowlist records.
