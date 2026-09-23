# Issue 256 Presentation Prefer-ladders Implementation Plan

## Baseline

Specification 59 and its architecture review establish that the requested
bounded capability is already present on `main`.  This plan deliberately has
no registry rewrite or package-schema slice: those changes would recreate the
rejected second presentation authority.

## Acceptance slices

1. **Ingress and decision audit.** Exercise schema acceptance and rejection
   for the closed View intent and ladder vocabulary.  Exercise a non-default
   item intent and assert that Layout records its requested ladder, selected
   rung, and outcome.
2. **Projection-boundary audit.** Run the structural Scene tests proving that
   Scene projects completed text/annotation placements rather than measuring,
   choosing a rung, or routing geometry.
3. **Public evidence gate.** Materialize the public examples, compare generated
   SVG bytes, run the full test and conformance suites, then record acceptance
   evidence.  Because the live capability is already covered, this is a
   verification-only implementation phase unless an audit exposes a missing
   invariant.  Such a finding returns work to design before any code change.

## Acceptance criteria

* The current View schema admits only Specification 59's finite vocabulary and
  rejects malformed intent/ladder data.
* Layout exposes deterministic selected-rung evidence for a non-default intent.
* Scene has no font-metric, rung-selection, or routing fallback.
* Existing public examples materialize and preserve committed SVG evidence.
* No profile-package field, dynamic presentation registry, or compatibility
  parser is introduced.
