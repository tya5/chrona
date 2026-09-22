# Typed Presentation Vocabulary Closure — Implementation Review

## Scope

Review P4.5 / issue #147 after P4 finalized the View v0.3 and subtree-summary
vocabulary.

## Result

Schema validation remains the one resource parsing seam.  It now creates
immutable named records for View rows, row items, table columns, selection,
grouping, ordering, window, comparison, visibility, Summary panels/metrics,
and Detail legend entries.  The render use case, projection, and v0.5 content
normalizer consume these contract records; the prior `projection_input`,
`summary_input`, and `detail_input` mapping escape hatches are removed.

## Boundary review

* The change is representation-only: Project scheduling, View selection/WBS
  semantics, Layout placement, Scene projection, and renderer policy are
  unchanged.
* Schema-accepted union payloads that are not yet separate semantic concepts
  (for example an annotation anchor) remain immutable closed values inside
  their owning named record; no raw resource document is passed downstream.
* Direct fixtures construct the same named records instead of bypassing the
  production contract boundary.

## Evidence

* Contract record and no-escape-hatch tests cover live resources and downstream
  source boundaries.
* Focused projection/summary/render tests pass.
* Full suite: **295 passed, 4 skipped**.

## Decision

P4.5 is ready for the materializer/publication gate.  #147 can be closed only
after that gate and two-platform CI are merged.
