# Issue #592 — surface composer implementation plan

Public design base: [`ffb8c8cd`](https://github.com/tya5/chrona/commit/ffb8c8cd6e18ed881522b41fada3756913d7e138). Predecessor: [design and whole-architecture review](issue-592-surface-composer-split-design-plan-2026-09-29.md), with the owner map in Spec 33 §8.3. This is a behavior-preserving Layout-internal extraction: no schema, resource migration, diagnostic, public API or generated-byte change is approved.

## Literal acceptance and common release gate

| Issue criterion (verbatim) | Direct evidence |
| --- | --- |
| `surface_composer.py` contains orchestration only, under about 400 lines. Each concern module has a docstring naming what it owns and what it reads. | Count source lines; inspect final coordinator and every new module docstring/read boundary. |
| Every public materializer and Scene is byte-identical, and the full test suite passes unchanged. | Compare all manifest-listed 29 SVG/Scene pairs with the design-base Git bytes after each slice, as one batch; final exact-main CI full pytest on the repository matrix. |
| The module reachability gate covers the new modules. | Run `tools/check_module_reachability.py` and import-direction gate after each extraction; inspect the gate's module list and final main CI. |
| Ownership notes are added to spec 33 (Layout ownership), so future issues can name the module they touch. | Spec 33 §8.3 published in design commit `ffb8c8cd`; final source/module map review. |

Before I592-1, record the manifest-derived output paths and design-base hashes from Git, plus focused test baselines. A zero-diff comparison is the acceptance oracle for this mechanical split; it does not bless an existing visual defect. Use one project venv and parallel batch render/check for SVG/Scene; do not rerender one slide at a time for review. Each slice below is a separate PR/merge/public base, with focused tests and generated-diff/reachability checks before acceptance. CI supplies the planned full matrix rather than duplicating a costly local full run.

| Slice | Owned files and typed boundary | Focused review |
| --- | --- | --- |
| I592-1 pure foundations | Extract `surface_geometry`, `surface_base`, and `surface_lanes` preflight helpers from `surface_composer.py`; add private typed base result. | Slot/row/scale, lane preflight, geometry tests; no import cycle. |
| I592-2 fixed geometry | Extract `surface_table`, `surface_groups`, `surface_axis`, `surface_backgrounds`; retain existing phase and tuple append order. | Table, group and axis placement tests; source-slot/target identity and overflow bytes. |
| I592-3 marks and visuals | Extract `surface_marks`, `surface_visuals` with typed mark/visual batches; keep Theme reads in Layout and preserve pattern/paint-order facts. | Mark, pattern, progress and visual reservation tests. |
| I592-4 shared obstacle phases | Extract `surface_member_labels` and `surface_routes`; pass one ordered `SurfaceObstacleIndex`, with pre-route as-of/lane-required labels and post-route optional labels. | Label/routing tests, #466 route priority, #467 lane visibility, obstacle registration order. |
| I592-5 remaining content | Extract `surface_legend`, `surface_content`, `surface_annotations`; preserve fixed-slot source placement before annotation search and connector topology. | Content, legend and annotation fixtures; no policy change to unfinished Spec 33 §8.2 successor. |
| I592-6 final composition | Extract `surface_completion`, final lane emissions and host identity; reduce `surface_composer.py` to typed phase calls/final assembly under ~400 lines. | Surface-quality/integration tests, module docstrings/reachability/import direction, all public bytes, final full CI. |
| A592 acceptance | Add one current review with four literal rows, exact commits/CI, hash comparison and architecture findings; close/archive only when all rows are met. | Confirm review-bearing main full CI and issue disposition. |

Do not combine a behavior correction with extraction. If moving a closure reveals an implicit ordering rule, missing typed result, or concern that cannot meet the owner map without duplicated mutable state, stop, publish a design correction and amend this plan before resuming. #590 derived-evidence workflow and #591 schema policy are independent; use their latest public gate when each code PR is submitted.
