# Design Plan — Collision-Aware Lane Rows as the Default (#467)

**Issue:** [#467](https://github.com/tya5/chrona/issues/467).
**Published baseline:** `b45be7b2104d2a94ce25ec6d328cf0743c254fac`
on GitHub `main`. The working tree has no tracked change at this baseline.
**Target:** [Transit Map research image](../../research/presentation/transit-target-2026-09-26/02-programme-board.png)
is a design reference, explicitly not renderer output.

## Published facts, inferences, and unverified points

- Published View v0.22 permits `rows.mode: automatic|explicit`; the corpus and
  packaged Draft default use `automatic`. View projection currently produces
  one row per selected object for every non-explicit mode. Layout allocates
  row bounds and mark tracks, while Specification 38 §3 still says Scene owns
  subtrack geometry. This authority inconsistency must be corrected in design.
- `explicit` item `track: stacked|shared` and `rows.points` folding are
  distinct existing mechanisms; neither is a general interval-packing rule.
  #440 records the name/date and group-header failures of point folds.
- The issue reports 26 automatic rows and a mark-only first-fit estimate of
  10 lanes on `02-programme-board`. The final lane count including measured
  labels, actual/baseline geometry and dependency-chain preference is not
  verified. The published target image was inspected, but its pixels do not
  prove materializer behavior.
- [#466](https://github.com/tya5/chrona/issues/466) proposes one shared
  obstacle model for labels, annotations and leader routes. The exact
  minimum #466 slice required by #467 has not been designed or published.
  Neither #466 nor #467 is complete by this plan alone.

## Literal issue acceptance

1. A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

## Use cases and decisions to close before code

The ordinary grouped Review should read as few chronological lines while
retaining each item's planned/actual/baseline footprint, name and delta.
`automatic` remains a deliberate full per-item table choice. Explicit View
rows must retain their View-owned membership and identity, but member
subtracks should be allocated by the same collision policy where admitted.

The design must settle, with fixture evidence, all of these questions:

1. Row versus lane identity: stable View row IDs, item IDs, source refs,
   group identity, relation/annotation anchors, and what changes when a
   nearby item is inserted. No coordinate or array-position identity.
2. Interval/footprint rules: inclusive point extents, touching spans,
   actual/baseline ghosts and lines, mark shapes/ports, measured plot labels
   and deltas, dependency paths, and temporal order. Define deterministic
   chain preference without globally reshuffling unrelated lanes.
3. Failure policy: a required name opens a new lane when no candidate fits;
   bounded search and truthful visible overflow remain compatible with #449.
   Explain density/canvas growth and the no-suppression invariant.
4. Layer ownership: View chooses `lanes` or `automatic`, grouping and
   authored explicit membership; Layout owns collision-aware lane, text,
   route and row geometry; Scene projects; adapters serialize. Reconcile
   Specifications 06, 08, 33, 38, 44 and 50 plus related ADRs.
5. Table semantics: a lane row's group/count/summary, item facts moved into
   plot labels or explicitly omitted, accessibility and source identity.
   Define interaction with existing table column grammar and explicit rows.
6. Defaults/migration: change new-View and packaged-preset defaults without
   silently changing immutable Context targets or current `automatic`
   output. Determine all resource mirrors and public materializers affected.
7. Dependency seam with #466: whether its shared obstacle set and candidate
   search must publish first. Do not duplicate a private obstacle index just
   for lanes, or declare all of #466 complete from a prerequisite subset.
8. #440 and #434 interaction: preserve `key-row` as separate successor work,
   and use existing `fill` distribution rather than a lane-specific canvas
   workaround.

## Design sequence and review evidence

1. Publish this design plan. Characterize current row, track, label, table,
   relation and annotation behavior with neutral and HALCYON fixtures.
2. Publish a joint ownership/obstacle-seam design for #466's needed slice,
   with its own literal criteria and publication boundary. Review whether
   that slice is independently useful before #467. Do not close #466 until
   its full issue acceptance is met.
3. Publish #467's selected row/lane contract, exact schema and defaults,
   deterministic algorithm, table/label policy, migration and diagnostic
   behavior. Update living specifications/ADRs, and publish a whole-
   architecture review that explicitly resolves Specification 38's stale
   Scene ownership statement and adjacent design constraints.
4. Publish an implementation plan with independently reviewable slices,
   files, schema/resource migrations, focused tests, generated Scene/SVG/PNG
   evidence, public materializer gates and commit/CI boundaries. Only then
   change product code.

Before acceptance, inspect the actual rendered 01/02/06 slides together;
check every required label and delta in adapter output, lane identity and
chain placement, deterministic insertion, automatic-mode byte parity,
generated diffs, conformance and public materializers, then CI's full matrix.
The release review must record direct evidence for all six literal rows.
