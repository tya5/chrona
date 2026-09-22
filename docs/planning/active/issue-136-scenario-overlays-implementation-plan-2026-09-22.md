# Issue 136 Scenario Overlays Implementation Plan

## Preconditions

The design in `issue-136-scenario-overlays-design-2026-09-22.md` is the
implementation authority.  Do not fold a Scenario into Snapshot storage or add
Scenario behavior in Layout, Scene, or a renderer.

## Independent slices

1. **S136-1 — Project contract and pure resolution.** Add Project v0.5,
   schema/typed contract, `ScenarioProvenance`, deterministic resolver, and
   scheduler-facing tests.  Atomically migrate all public Project resources and
   Profile requirements.  Verify merge semantics, frame rejection, derived
   validation, scheduler non-mutation, full pytest, materializer reproduction.
2. **S136-2 — View and closure integration.** Add View v0.7 and typed View
   contract; add scenario baseline/explicit rows, closure provenance, render
   ledger, projection and normalized table/summary sources.  Verify scenario /
   snapshot distinction, source alignment, diagnostics, full pytest, public
   materializer checks.
3. **S136-3 — Evidence and release gate.** Add a HALCYON scenario context and
   generated evidence, validate deterministic Scenario materialization and
   output properties, conduct an architecture-boundary review, run focused and
   full suites, inspect generated SVG diffs, then close #136.

Every slice is a separate PR.  Before each merge, fetch `origin/main`, inspect
the exact commit range and PR merge state, wait for all CI checks, then merge
serially without force push.
