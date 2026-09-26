# Implementation Plan — Collision-Aware Lane Rows (#467)

**Design base:** [selected design](../../design/issue-467-collision-aware-lane-rows-design-2026-09-26.md), [whole-architecture review](../../reviews/current/issue-467-collision-aware-lane-rows-architecture-review-2026-09-26.md), and [Specification 38](../../specification/38-review-row-composition.md), published at `c8ff46f17f348a8bb8ee88ad277a1e7004388972`.
**Prerequisite:** complete and publish [#466 obstacle-only stage](issue-466-shared-obstacle-prerequisite-implementation-plan-2026-09-26.md) before accepting lane code. #466 remains open for its other criteria.

## Literal #467 acceptance ledger

1. A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane.
2. Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide.
3. Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes.
4. Deltas remain visible for packed items that have them.
5. New Views and the packaged presets default to lanes; `automatic` still renders exactly as today.
6. At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible.

## Slice order and acceptance

| Slice | Owners/files and migration | Focused tests/evidence | Publication |
| --- | --- | --- | --- |
| L0 measured feasibility | A neutral, non-product prototype in `tests/unit/chrona/presentation/layout/` or a documented fixture; no schema/resource mutation | Compute closed mark+name/delta candidate footprints for HALCYON 02 with actual font metrics; demonstrate ≤12 lanes and the named chain, or return to design with a published correction | Publish feasibility record with this plan before L1 product code if design needs changing |
| L1 v0.23 authoring contract | `schemas/view-v0.23.schema.yaml`, wheel schema packaging rules if needed, `contracts/resources.py`, schema registry, typed `ViewRows`/lane table intent, normalization; schema/integration tests and conformance fixtures | Reject item table columns/hierarchy/points/invalid labels in `lanes`; exact `automatic` and v0.22 validation parity; wheel-installed schema identity | Commit/push schema-contract slice; CI full matrix |
| L2 Layout lane engine | `layout/obstacles.py`, new lane allocation module, `layout/presentation.py`, `layout/surface_composer.py`, typed placement records, `model/surface_content.py`, `review/v05_content.py`; no Scene-owned geometry | Neutral overlap/touching/actual/baseline/point/label tests; chain and insertion stability; explicit v0.23 collision opt-in; required name and delta; item/port identity; #468 host growth; automatic byte characterization | Commit/push independent engine slice; focused tests and CI; if ≤12 fails, stop for design correction |
| L3 View defaults and three slides | `examples/halcyon-1/views/01-mission-brief.yaml`, `02-programme-board.yaml`, one non-hierarchy third View (candidate 03 or 04), `default-draft.yaml`, packaged preset/resource mirrors and starter templates; public generated Scene/SVG/PNG | Review removed per-item table facts and selected label facts per slide; inspect name/delta visibility and no suppression in adapter output; 02 lane count/chain; default preset actually selects lanes; v0.22 automatic bytes unchanged | Commit/push corpus migration and regenerated public evidence atomically; CI newest-Python materializer and full matrix |
| L4 acceptance and close | `docs/reviews/current/issue-467-collision-aware-lane-rows-acceptance-review-2026-09-26.md` using acceptance template | Exact commit/PR/CI links, test commands, Scene/SVG/PNG diff batch, six literal rows with direct evidence, architecture and regression review | Publish review; close #467 only when every row is met and CI green; #466 stays open |

L0 is a hard design-validation gate, not a loophole to weaken the acceptance threshold or hard-code HALCYON coordinates. L2 must use one #466 inventory, not a second lane-only collision list. Item IDs and source refs stay stable while generated row IDs use stable group/representative identities; labels and relation routes are Layout placements; Scene only projects. The `automatic` mode must not change due to the lane feature (an independently justified #466 obstacle correction may have its own reviewed byte diff).

For each slice run local focused pytest in `.venv311`, public materializer checks when outputs can change, and batch-inspect all affected generated Scene/SVG/PNG. Use the planned CI three-OS full pytest/conformance and newest-Python public reproduction instead of a duplicate full local run. Before each serial push fetch `origin/main`, inspect exact staged diff and conflict risk; after push verify remote commit and run state. A new schema/ownership/failure-rule gap returns to design/review and an implementation-plan amendment before code resumes.
