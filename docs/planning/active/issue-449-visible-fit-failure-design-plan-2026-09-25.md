# Design Plan — Visible Fit and Placement Failure Policy (#449)

**Status:** planning correction required before further #400 implementation.
**Supersedes:** the refuse-on-`diagnose` portions of ADR-0031 and the #400
visible-row-density design and implementation plans.

## Trigger and public baseline

The owner decision in #449 is authoritative: a fit or placement condition must
not prevent Chrona from producing a slide.  It must produce completed geometry
that makes the condition visible and an inspectable warning.  Invalid input,
missing resources, and integrity failures remain render-stopping errors.

The uncommitted I400-1 migration to a `rowDensity` policy with an immutable
`diagnose` refusal is therefore not an implementation candidate.  It is held
outside publication until this correction has supplied a replacement contract.
The completed #405–#408 axis evidence remains useful, but its refusal branch
must be evaluated under this decision rather than retained by implication.

## Measured scope

At `dc2dfb36`, fit/placement diagnostics occur at approximately fifty literal
sites across Layout and render ingress, including required slot overflow,
network overflow, label placement, axis fitting, route limits, mark
containment, table feasibility, relation labels, and folded group headers.
The design must distinguish:

1. a user-visible render decision that currently prevents an artifact;
2. an internal candidate-rejection or minimum-requirement predicate that may
   remain an implementation detail when a visible completed fallback consumes
   it; and
3. invalid/inconsistent input, missing-resource, or integrity errors that are
   explicitly out of scope for the no-refusal policy.

No count from the issue body substitutes for the source-derived registry.

## Questions the design must answer

1. Publish a finite, source-derived registry mapping every user-reachable
   fit/placement failure family to its Layout-owned visible fallback, warning
   code/payload, and completed placement evidence.  The registry must cover
   every current refusal family, not only review rows.
2. Replace the old meaning of generic `overflow: diagnose`.  It may not cause
   a fit/placement refusal.  Decide whether it is renamed/migrated or means
   deterministic natural-size visible overflow with a warning; retain
   `ellipsize-with-source`, `clip-optional`, wrapping, thinning, and
   suppression only as explicit author choices.
3. Define physical geometry for each fallback: natural-size slot escape,
   surface/canvas growth where the output contract admits it, preferred-label
   overlap, all axis labels, direct relation path, stacked group-header items,
   and visible mark overflow.  A fallback may not become adapter-local crop,
   silent suppression, or Scene-side geometry selection.
4. Define the typed Layout outcome and warning transport.  Layout must return
   all geometry and structured warning facts; Scene only projects them; the
   CLI reports warnings after successful rendering.  The published Scene must
   let #446-style perceptibility gates count every fallback without rerunning
   policy.
5. Reconcile fixed and auto viewports with visible overflow.  In particular,
   specify when a surface expands its completed bounds and when an in-canvas
   slot escape is the only truthful representation.  The design must not
   promise visibility outside an SVG/PDF viewport that clips it.
6. Amend ADR-0031 (or publish a superseding ADR) and Specifications 08/50 so
   their feasibility language names completed visible fallback rather than
   rejection.  Review the result against the Project/View/Profile → Layout →
   Scene → adapter boundary.
7. Specify an all-at-once schema/corpus migration for the current overflow
   declarations.  There must be no compatibility reader, hidden per-renderer
   default, or period in which existing public Contexts become unrenderable.

## Required design outputs

The resulting English design must include the finite registry, a disposition
matrix, typed data-flow and geometry diagrams, warning schema, viewport and
target matrix, migration inventory, negative boundary tests, and a full test
matrix.  Its architecture review must prove that Layout is still the sole
geometry/policy authority and that the Scene/adapters cannot infer a fallback.

## Implementation sequencing constraints

The implementation plan may split work by independent warning/placement
families only after the common outcome contract and migration are accepted.
Each slice must keep every affected public Context materializable.  A release
gate must regenerate public artifacts in one batch, review SVG/PNG changes,
run full pytest, conformance, all public materializers, wheel smoke and
three-platform CI, then publish an acceptance review before #400/#449 close.

No implementation may publish the current I400-1 `diagnose` refusal contract,
globally weaken a primitive invariant without an explicit visible placement,
or retain a render-use-case preflight that rejects a fit/placement condition.
