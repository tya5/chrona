# Design Correction — Purpose-Independent Annotation Placement (#413)

**Status:** Design correction complete; amends the #413 semantic visual
realization design and I413-2 implementation plan.

## Trigger

The initial annotation implementation applies the View-declared annotation
fallback ladder only to `callout` and `explanatory-arrow`.  `highlight` and
`note` instead attempt one direct side placement in the annotation slot.  A
single public slide that truthfully exercises all four admitted purposes then
cannot be materialized when a direct side lies outside that slot.

This is not a corpus-fixture problem.  Placement choice is Layout geometry, and
the purpose of an annotation controls its semantic treatment and leader, not
whether it receives a failure-policy ladder.

## Correction

Every typed `AnnotationIntent` carries the same View-normalized annotation
fallback ladder.  Layout applies that ladder to each finite purpose:

* a side rung uses the existing measured annotation-box projection;
* a `rail` rung uses the existing measured annotation rail;
* `suppress` records the existing explicit suppression decision.

The selected rung is retained in the completed placement decision.  The
purpose-specific `AnnotationPresentation` remains separate and supplies box,
text, leader, and terminal semantics only.  `highlight` has no leader;
`callout` and `note` have plain leaders; `explanatory-arrow` has the declared
target marker.  Thus the fallback mechanism cannot infer or erase purpose.

## Ownership and constraints

View declares the finite ladder; normalization closes it into typed content;
Layout measures, selects, and records a rung; Scene projects the completed
semantic placements and never chooses a rung or route.  No renderer fallback,
purpose-specific coordinate shortcut, or corpus-only exception is permitted.

## Acceptance additions

I413-2 must prove that all four purposes can independently use the declared
ladder, that a suppressed annotation has no box/text/leader primitive, and
that changing a purpose does not change the ladder authority.  The Controller
Z corpus must realize all four purposes through this common path.
