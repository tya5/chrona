# Design Plan — Composited Role Contrast and Corpus Visibility (#431)

## Problem

The released Scene perceptibility evaluator can report composited paint facts,
but it deliberately has no role-class policy or threshold.  As a result,
background decorations can be emitted indistinguishably from their ground and
state-coloured text can be emitted below its readability floor.

## Established facts

- `scene.perceptibility` already owns renderer-neutral hex compositing and
  contrast observation over completed Scene mappings; #431 must not create a
  second raster or adapter-specific contrast calculation.
- `color_scheme.resolve_color_scheme` validates ordinary text and
  `resolve_theme` validates inside labels before Scene construction.  Neither
  can decide a decoration's completed opacity and ground relationship.
- The semantic registry identifies the candidate decoration and state-text
  roles.  It is the source for finite classification, not primitive-name or
  visual-heuristic matching.
- #446's public checker reports all observations but does not select floors.
  #431 owns class policy, thresholds, explicit absence, corpus migration, and
  the checked per-purpose report.

## Questions

1. Which finite semantic role classes are required text, optional decoration,
   and explicitly absent decoration; which classes have a declared floor?
2. At which Theme/closure and completed-Scene boundaries are class intent,
   opacity, ground, and contrast each validated without duplicating the
   perceptibility evaluator?
3. How is `none` represented as a typed resolved paint disposition so that an
   omitted decoration cannot be confused with one painted invisibly?
4. What stable diagnostic and report forms distinguish an invalid Theme from a
   corpus artifact that violates a completed-Scene floor?
5. How will light and dark corpus themes, generated Scenes/SVGs, inventories,
   and public materializer evidence migrate atomically?

## Deliverables

- English architecture design and whole-system boundary review.
- An implementation plan with independent policy, migration, report, and
  release slices.
- A finite role-class and threshold contract that reuses #446's common pure
  composition kernel.
- Literal acceptance evidence for every #431 acceptance bullet.
