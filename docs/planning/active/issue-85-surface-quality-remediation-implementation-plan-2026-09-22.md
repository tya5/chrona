# Issue 85 — Surface Quality Remediation Implementation Plan

**Status:** Approved implementation plan.  **Issue:** #85.
**Design authority:** `issue-85-surface-quality-remediation-design-review-2026-09-22.md`.

## Publication rule

Each slice is an independent PR from freshly fetched `main`.  Before merge it
requires focused tests, full pytest, conformance, reachability/import checks,
five public materializers, generated-SVG diff inspection and CI.  A later slice
does not begin before its predecessor is merged.

## C85-1 — Table semantic correctness

**Files:** content normalizer/formatting tests, render-usecase locale handoff,
HALCYON mission/launch generated SVGs, and the point-row property pins.

- Normalize `actual` absence against item kind, planned interval and Actual
  cutoff; never emit `in progress` for points or future spans.
- Make `dateRange` deterministic compact `en-US` output using the Context
  locale; retain cross-year precision.
- Add neutral unit cases for each Actual state and range form; public examples
  prove the changed labels and remove only the point-row pins.

**Acceptance:** all point-row property cases pass; no scheduler/Layout/Scene
change; expected materializers remain reproducible.

## C85-2 — Plot text and table feasibility

**Files:** Layout request/placement helpers, surface composer, optional Theme
metric resolver and affected Themes/Layout tests; no Scene routing/measurement.

- Route member labels and standalone finish deltas through one deterministic
  Layout candidate/obstacle solver.
- Add and enforce positive `table.column.gutter.inlineSize` in feasibility and
  allocation.
- Add neutral collision/gutter tests and public examples; remove only the
  plot-over-mark and viewport pins when their exact fingerprints pass.

**Acceptance:** all accepted plot text lies in the timeline and is non-overlap;
table text has a positive measured gutter; no duplicate delta is emitted.

## C85-3 — Slot content, groups and closure density

**Files:** complete surface-content facts, Layout calendar/group handling,
ASTER/controller detail profiles and contexts, relevant layout priorities,
HALCYON Theme metrics, tests and generated artifacts.

- Carry calendar exception closures explicitly and apply the declared density
  metric in Layout.
- Bind intentional legend content; make ASTER notes explicitly optional; verify
  group headers only where the View selects them.
- Remove only resolved empty-slot pins, with neutral source/slot/density tests.

**Acceptance:** no required declared content slot is silently empty; exceptions
remain visible at narrow scales; all authoring closures materialize.

## C85-4 — Monochrome form serialization

**Files:** `ThemeTokenView`, SVG adapter, renderer tests, print Theme/SVG.

- Resolve optional declared pattern intent; serialize solid, outline and
  diagonal-hatch deterministically from completed primitive roles.
- Add explicit print Theme form/stroke bindings and generated evidence.

**Acceptance:** no renderer-side semantic selection; plan/actual/missing actual
are distinguishable in the print SVG and colour themes remain byte-stable.

## C85-5 — Final review

Run all gates, inspect the complete generated diff and rasterized changed SVGs,
verify Scene has no font/routing imports and renderers have no Layout/closure
imports, then close #85 only with no remaining #85 acceptance pins.

## Exclusions

No View schema version, Project schema, scheduler, draft path, renderer-port or
output-format change is authorized by this plan.  If a slice needs one, stop
implementation and return to a published design correction.
