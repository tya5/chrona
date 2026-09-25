# Design Plan — Cross-Python Public Evidence Reproduction (#442)

**Status:** active; implementation is not authorized by this document.

## Trigger and factual baseline

Issue #442 establishes a concrete public-reproduction failure: the committed
HALCYON `mission-brief`, `gallery-dark`, and `gallery-mono` Scene artifacts
reproduce on Python 3.12 but not on the supported Python 3.11 CI interpreter.
The visible SVGs agree after their three-decimal serialization, while Scene
JSON differs in final float digits in table-column coordinates.  The immediate
source is builtin floating-point accumulation in Layout table allocation;
Python 3.12's compensated `sum` changed its result.

This is a release-integrity defect, not a README defect.  #412 changes the
same generated Scene corpus, so its atomic evidence release cannot be
published against an interpreter-dependent arithmetic boundary.

## Scope and non-goals

The correction must make every float accumulation that can feed a completed
Layout placement deterministic across all supported Python minors.  It must
also make CI exercise public corpus reproduction on Python 3.11 and the
newest supported minor.

It does not change visual policy, introduce a new provenance field, round
geometry merely to hide a difference, narrow the declared Python support, or
make renderer output the authority for Scene geometry.  Decimal-only
accumulations and integer/count accumulations are not the defect, but their
classification must be explicit so a future float placement sum cannot evade
the rule.

## Design questions to close

1. Define one Layout-owned deterministic accumulation primitive and its
   numeric-domain contract.  It must not silently coerce Decimal layout values
   to float or introduce per-call rounding policy.
2. Inventory every `sum` under `chrona.presentation`, classifying it as
   integer/count, Decimal, non-placement validation, or float geometry.  Move
   all float geometry accumulations that influence bounds, ports, allocation,
   fit, routing quality, or placement decisions to the primitive.
3. Define a structural regression check which rejects direct builtin float
   accumulation in Layout placement paths while allowing intentional Decimal
   and count sums with explicit evidence.
4. Define evidence migration: regenerate the complete public corpus only after
   deterministic arithmetic lands, then prove byte reproduction on both
   supported interpreter minors.  Do not regenerate just the three observed
   failures.
5. Define CI topology that keeps the existing cross-platform Python 3.11
   conformance gate and adds an Ubuntu newest-minor corpus-reproduction gate.
   The latter must invoke the actual public materializer check, not a synthetic
   numeric test.
6. Decide provenance semantics.  The expected answer must explain why an
   interpreter identity is not a substitute for deterministic Layout output,
   and whether any write restriction is needed after CI provides the matrix.

## Required design outputs

The completed English design must include the numeric ownership boundary,
call-site classification, no-rounding rule, test/CI matrix, generated-artifact
migration, and an architecture review against Layout/Scene/materializer
separation.  It must state how #412 consumes the repaired evidence boundary
without coupling orientation semantics to Python version.

## Publication sequence

1. Publish this plan.
2. Publish the completed design and architecture review.
3. Publish an implementation plan with independently reviewable arithmetic,
   structural-test, corpus-evidence, and CI slices.
4. Implement the approved slices, regenerate all public evidence, and verify
   both interpreter minors before resuming #412's release gate.

## Acceptance of this planning phase

The plan is ready for design only when it preserves the public requirement:
the same immutable inputs must produce byte-identical public Scene evidence
on every supported interpreter, rather than merely accepting interpreter-
specific evidence.
