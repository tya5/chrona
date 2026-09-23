# Design Correction: Visual Composition Completion (#350)

**Status:** Complete — amends I350R-4 before its implementation can be
accepted.

## Observed implementation divergence

The published View Visual Target Closure establishes that Layout owns all
visual geometry and that `icon_bindings` is removed atomically. The partial
I350R-4 implementation correctly carries typed requests to Layout, but its
composition is not yet closed:

1. `mark` is schema-admissible but only text placements are resolved.
2. A label visual reduces already-completed text bounds instead of reserving
   advances before measurement, wrapping, ellipsizing, and overflow.
3. Visual size and gap use local numeric constants instead of Theme ratios.
4. The legacy `icon_bindings` request path remains alongside `visuals`.

These are ownership and schema-door defects, not follow-up polish. I350R-4
therefore remains incomplete until one atomic successor path replaces them.

## Corrected composition contract

Each typography role that can host a text visual declares finite,
non-negative `iconScale` and `iconGap` number-token bindings in Theme. A
visual's block size is `fontSize * iconScale`; its inline gap is
`fontSize * iconGap`. The resolved Theme carries these bindings unchanged to
Layout. No fixed pixel fallback is permitted. All shipped Themes must declare
the bindings, so a missing ratio is a closed Theme diagnostic rather than a
rendering heuristic.

For a text target, Layout first resolves all direct/encoded icon requests,
then reserves the aggregate leading and trailing advances from the target's
available inline extent. It re-runs the target's existing measured overflow
policy on the reduced extent: fit remains fit, ellipsize-with-source uses its
source text, and wrapping uses the target's declared or previous line policy.
It emits the reduced text bounds, baseline, lines, overflow result, icon
bounds aligned to measured cap height, and logical visual order as one
placement closure. Insufficient required extent rejects with the existing
required-overflow diagnostic.

For a `mark` target, Layout resolves exactly one completed planned or actual
mark placement selected by object and facet. It fits the normalized asset to
the named mark bounds while preserving aspect ratio, centres it in that mark,
and emits an `iconMark` placement. Text-side reservation is inapplicable to
marks; a mark declaration still participates in duplicate-target validation.

`VisualRequest` is the only intent path from View to Layout. `icon_bindings`
is removed from Scene input, Layout request, composition, tests, and all
callers in the same commit. Scene receives completed placements only.

## Architecture consistency review

The correction preserves the published authority chain: View selects a closed
occurrence; Context resolves assets; Theme supplies only ratios and paint;
Layout computes all geometry and overflow; Scene projects; adapters serialize.
It adds neither a new asset-selection authority nor adapter measurement, and
it leaves Project/Actual facts and mark geometry unchanged. The typed mark
projection closes the only remaining schema-valid but unprojected target.
Requiring Theme ratios removes a local layout policy and keeps
typography-relative sizing portable across Themes.

## Atomic acceptance evidence

I350R-4 must demonstrate all of the following together:

- every target in the v0.12 inventory, including planned and actual marks,
  reaches exactly one Layout placement or rejects before projection;
- leading and trailing visuals are reserved before text remeasurement, with
  fit, ellipsize, wrap, and insufficient-space cases characterized;
- changing declared Theme ratios or typography changes Layout geometry without
  a Scene or adapter change;
- no source, model, or test runtime path exposes `icon_bindings`;
- Scene projects completed label and mark icon placements without measuring,
  resolving a catalog, or selecting an occurrence.
