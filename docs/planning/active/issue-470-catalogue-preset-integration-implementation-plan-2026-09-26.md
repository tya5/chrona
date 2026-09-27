# Implementation Plan — Five Preset PR Merges (#470)

**Design:** [integration contract](../../design/issue-470-catalogue-preset-integration-design-2026-09-26.md) and [whole-architecture review](../../reviews/current/issue-470-catalogue-preset-integration-architecture-review-2026-09-26.md), published at `fc2574176c0330eadc8a0936b1d284815db86974`. **Base gate:** #466 C1 `d271b175` passed its [material CI](https://github.com/tya5/chrona/actions/runs/36233858722) and [acceptance review](../../reviews/current/issue-466-candidate-normalization-implementation-review-2026-09-26.md).

## Literal acceptance ledger

1. Each of the five presets has its own members and a merged tuning PR with before/after images on HALCYON-1 and the `chrona init` starter.
2. Every preset renders HALCYON-1 at 1600 × 900 without `W_LAYOUT_*` or `W_SCENE_TEXT_INTERSECTION` warnings.
3. Every mechanism gap found is either filed as its own issue or attached to an existing one.

The requested viewport versus natural output dimension interpretation is fixed in the design; record both in final evidence.

## Serial publishable slices

| Slice | Files and owner | Focused gate | Publication and acceptance |
| --- | --- | --- | --- |
| P470-1 | PR #471 `mission-light` bundle, its `library.yaml` entry, packaged-resource test and research images | Inspect exact PR diff/head/reviews; copy preset and render HALCYON/starter; warning inventory; compare current vs PR images; packaged-resource test; public materializer byte check | Merge #471 only after green current-base validation; confirm merge commit and current-main CI before next merge. |
| P470-2 | PR #472 `control-room-dark`, same per-preset owners | Same, including dark paint legibility and source terminal | Serial merge and current-main CI. |
| P470-3 | PR #473 `print-mono`, same per-preset owners | Same, including actual output size and explicit #483 monochrome limitation | Serial merge and current-main CI. |
| P470-4 | PR #474 `executive-light`, same per-preset owners | Same, including row-guide/bar-label readability, all label/route warnings, requested/actual size | Serial merge and current-main CI. |
| P470-5 | PR #475 `elevated-light`, same per-preset owners | Same under default and declared v0.7 PNG profile; record #479/#478 profile limitations | Serial merge and current-main CI. |
| P470-6 | Acceptance review, issue disposition | Batch copied-preset HALCYON/starter renders, actual SVG/PNG inspection, zero named HALCYON warnings, gap map #476–#483/#466, full three-OS/newest CI and public materializers | Publish review separately; close #470 only when every literal row is met. |

Before every merge/push, fetch `origin/main`, inspect remote updates, exact PR head, changed files and conflict risk. No force push, reset-hard or broad checkout. Existing PR branches are not modified unless a normal follow-up is required; stop on unexpected remote changes. CI full tests run in GitHub; locally run focused packaged-resource checks and batch render/evidence scripts, not repeated full pytest. A failed required check or a new HALCYON warning blocks that slice. Do not infer acceptance from PR prose or a Scene-only report.
