# Design Correction — Visible Axis Overflow and the P0 Corpus (#443)

**Corrects:** `issue-454-p0-p1-p2-remediation-architecture-design-2026-09-26.md`
and the completed #443 rollout.
**Status:** Proposed for architecture review before corrective implementation.

## Finding

The completed P0 corpus audit finds a real intersection in
`halcyon-1/07-replan-baseline`: the horizontal `Jun` and `Jul` labels in the
month tier overlap by approximately 0.835 points.  The tier declares
`overflow: visible-overflow`.  That is a valid #449 fallback: all named
labels remain visible and the completed Scene records the overflow.  It is not
compatible with #443's literal corpus acceptance that no two committed axis
labels intersect.

The prior #454 architecture text incorrectly stated that visible overflow
could not make an ordinary axis intersection valid.  That would silently
redefine the published #449 registry, whose axis-density row explicitly
permits visible labels including overlaps.  The correction preserves that
general contract and makes the public corpus choose its already-declared
non-overlap alternative.

## Decision

`visible-overflow` remains a finite Layout outcome for an author who elects
to retain every declared axis label, including a deterministic overlap and
its `W_LAYOUT_AXIS_OVERFLOW` fact.  It is neither an error nor a Scene or
adapter decision.

The P0 corpus is stricter: every committed axis label tier that would produce
a positive-area text intersection must declare `thin-with-record` (or another
future explicitly designed non-overlap policy).  The correction changes the
Controller-independent `07-replan-baseline` month tier from
`visible-overflow` to `thin-with-record`.  Layout's existing deterministic
thinning selects retained candidates and records every omitted candidate and
the density record before Scene construction.

This is a View policy correction, not a coordinate nudge, renderer crop, or
numeric exception.  The measurement, lane allocation, one axis collision
domain, Scene projection, and #449 visible-overflow implementation remain
unchanged.

## Consequences and invariants

1. The #443 acceptance audit requires zero positive-area axis-label
   intersections across all committed generated Scenes, measured at the
   Layout micro-point tolerance.
2. The replan month tier has a deterministic thinning decision and Scene
   diagnostics for omitted candidates; no omission is silent.
3. A separately authored `visible-overflow` tier continues to serialize every
   completed label and its warning.  This correction does not remove that
   supported policy or reinterpret it as a failure.
4. Scene, renderers, and the future #446 evaluator only observe the completed
   outcomes.  They do not choose thinning or suppress an overlap.
5. The P0 acceptance review distinguishes the general #449 contract from the
   stricter selected public-corpus policy; it must not claim that all valid
   author inputs are globally non-overlapping.

## Required evidence

- focused View/Layout coverage proves the replan tier records deterministic
  thinning and has no remaining axis-label intersection;
- regenerated replan public Scene/SVG evidence contains the recorded outcome;
- the completed-corpus Scene audit reports zero #443 intersections using the
  micro-point tolerance, while a dedicated `visible-overflow` fixture still
  proves the #449 fallback;
- architecture review confirms that the correction preserves the one-way
  intent → Layout → Scene → adapter boundary and does not encode a #446
  allowlist.
