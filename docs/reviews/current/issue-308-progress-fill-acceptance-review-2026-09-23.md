# Issue #308 Progress Fill Acceptance Review

**Status:** Accepted  
**Date:** 2026-09-23  
**Design:** [Specification 61](../../specification/61-progress-fill-marks.md)  
**Implementation plan:** [Issue #308 plan](../../planning/active/issue-308-progress-fill-implementation-plan-2026-09-23.md)

## Delivered contract

View v0.10 declares the closed `progressFill.source` choice (`actual` or
`planned`).  Layout derives an optional, renderer-neutral
`progress-fill:<host-id>` rectangle from the corresponding completed host mark
and fraction.  Scene projects only that completed placement through the closed
`progressFill` semantic binding; it neither measures text nor calculates
progress geometry.  All shipped themes bind the distinct `progress-fill` paint
role, and the HALCYON programme-board is public evidence for planned progress.

The accessibility-boundary correction records that the existing Scene contract
provides source reference and semantic purpose, while percentage prose awaits a
future versioned metadata contract.  This preserves the Layout → Scene →
adapter responsibility boundary without an SVG-only exception.

## Acceptance evidence

| Gate | Result |
| --- | --- |
| Focused layout, schema, Scene-boundary, and materialization tests | `69 passed` |
| Full test suite | `451 passed, 7 skipped` |
| Schema conformance | pass |
| All eight declared public materializers | byte-identical; generated-SVG diff empty |
| Built-wheel installed-smoke test | pass |

The progress-fill helper covers zero omission, fractional width, full-host
width, and invalid fractions.  The structural Scene test rejects direct use of
the Layout geometry helper, guarding the intended projection-only boundary.

## Scope review

This closes only the remaining #308 display fill.  #310 inside labels and #314
declared colour scales remain independent completed contracts; no compatibility
layer, schedule behavior, Actual selection, or colour-scale policy was added.
