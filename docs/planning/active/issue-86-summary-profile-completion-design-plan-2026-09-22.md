# Issue 86 — Summary Profile Completion Design Plan

**Status:** Proposed design plan.  **Issue:** #86.  **Baseline:** `9a79d77`.

## Purpose

Close the remaining closure-consumption and placement gap for `summary-profile`
without restoring a second presentation path or moving layout policy into Scene.
The review render must consume a bound summary profile, measure exactly the text
it will place before slot allocation, and emit the completed result through the
existing Layout → Scene → renderer seam.

## Confirmed baseline

- `RenderClosure` already has a typed `SummaryProfileContract`, but
  `render_review()` neither reads it in its ledger nor passes it to content
  normalization.  The three HALCYON contexts that bind it therefore fail the
  optional input-read gate with `summary-profile` unused.
- The use case measures a stub `SourceInput(("summary",))` before Layout.
  That one line is not the authored panel, so a `blockSize: content` summary
  slot cannot reserve its actual height.
- `figures` emits a `metric` value and a `summary` caption.  The composer
  advances both with the summary line height.  This is invalid whenever the
  metric typography is larger, as it is in the wallboard theme.
- The typed detail profile is now consumed.  It remains layout-manifest
  dependent and must not be folded into a pre-layout normalization result.

## Questions to settle in design

1. Define the minimum typed, pre-layout presentation fact that can supply
   summary measurements without constructing a partial `SurfaceContentInput`.
2. Define one canonical sequence of summary text runs shared by measurement
   and placement, including mixed typography in `figures` panels.
3. Define the allocation and overflow contract for a content-sized summary
   slot, including its relationship with neighbouring notes and legend slots.
4. Establish whether the HALCYON wallboard's missing `metric.fill` is an
   authored-resource correction or a renderer fallback.  The design must keep
   Theme as the sole paint authority.
5. Review the proposed boundary against Specification 08, Specification 09,
   Specification 50, ADR-0031, and the completed Issue 94 / Issue 99 source
   architecture.

## Non-goals

- No new summary schema syntax, visual policy, or renderer primitive.
- No change to legend, group-header, plot-label, table, monochrome, or calendar
  quality findings tracked by #85.
- No compatibility fallback for an unconsumed closure resource, no duplicate
  render route, and no regenerated artifact before the design explicitly
  authorizes it.

## Required evidence for design completion

The design review must identify one owner for summary semantic facts, source
measurement, geometry, primitive projection, and paint; show why the change
does not create a second authority; list the exact authoring changes needed to
make every affected public materializer valid; and prescribe independent,
reviewable implementation slices with acceptance tests.

## Publication gate

This plan and its design review are published before an implementation plan is
written.  No source or generated-output change is authorized by this document.
