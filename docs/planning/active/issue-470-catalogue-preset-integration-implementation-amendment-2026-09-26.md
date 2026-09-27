# Implementation Plan Amendment — Combined Preset PR #485 (#470)

**Supersedes:** P470-1 through P470-6 publication topology and the strict
all-`W_LAYOUT_*` gate in the [original implementation plan](issue-470-catalogue-preset-integration-implementation-plan-2026-09-26.md). **Approved design:** [correction](../../design/issue-470-catalogue-preset-integration-correction-2026-09-26.md) and [architecture review](../../reviews/current/issue-470-catalogue-preset-integration-correction-architecture-review-2026-09-26.md).

## Current literal acceptance ledger

1. Each of the five presets has its own members and a merged tuning PR with
   before/after images on HALCYON-1 and the `chrona init` starter.
2. Every preset renders HALCYON-1 with a requested 1600 × 900 viewport, and
   the canvas may grow, without any layout failure in CLI or Scene diagnostics:
   `W_LAYOUT_*OVERFLOW*`, `W_LAYOUT_ROW_DENSITY`, or
   `W_SCENE_TEXT_INTERSECTION`. The truthful TVAC incomplete-Actual and
   declared label-suppression diagnostics may remain.
3. Every mechanism gap found is filed separately or attached to an existing
   issue.

## Publishable slices

| Slice | Owned change and gates | Publication |
| --- | --- | --- |
| P470-C1 | Review #485 exact head and diff against current `origin/main`; confirm five distinct bundle members, complete sorted packaged-resource union, unchanged default and no mechanism/schema/corpus edits. Inspect all five README/image pairs as a batch. Check current-base mergeability and all required PR CI jobs. Reproduce copied-preset HALCYON/starter renders and classify **both** CLI and Scene diagnostics by the literal failure gate. Run packaged-resource focused test and public materializer batch. | Merge only #485, without force or overwriting an unexpected remote update; verify PR merge and new `main` commit. |
| P470-C2 | Re-run copied-preset renders on actual merged `main`, inspect all dimensions/diagnostics and output images, and verify issue gap mapping #476–#483/#466. Correct the five research READMEs' unqualified "no warnings" wording to the accepted layout-failure gate, preserving the images. Inspect post-merge full CI matrix and newest-Python materializers. Create a row for each literal criterion with direct links and artifact evidence. | Publish documentation correction and acceptance review as coherent follow-ups; close #470 only after every row and reviewer post-review are complete. |

Before each push or merge fetch `origin/main`, compare exact target and remote
ahead/behind state, inspect staged/PR diffs and conflict risk. CI supplies full
pytest/conformance/wheel-smoke; focused local tests and one batch of public
materializers suffice. Do not merge #471–#475 separately or suppress a factual
diagnostic. A newly discovered ownership or semantic gap returns to a
published design correction before implementation resumes.
