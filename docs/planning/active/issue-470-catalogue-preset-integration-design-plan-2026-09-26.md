# Design Plan — Integrate Five Catalogue Preset Tuning PRs (#470)

**Issue:** [#470](https://github.com/tya5/chrona/issues/470), read with all comments (none) on 2026-09-26. **Current public base:** `cbcc85e9` accepts #466 C1 after [green four-job CI](https://github.com/tya5/chrona/actions/runs/36233858722). **Inputs:** independent open PRs [#471](https://github.com/tya5/chrona/pull/471), [#472](https://github.com/tya5/chrona/pull/472), [#473](https://github.com/tya5/chrona/pull/473), [#474](https://github.com/tya5/chrona/pull/474), [#475](https://github.com/tya5/chrona/pull/475). Their existing green checks ran against older `main` revisions; mergeability and behavior must be refreshed against the integration base. The issue's YAML-only implementation proposal is a lead, not acceptance proof.

## Literal acceptance

1. Each of the five presets has its own members and a merged tuning PR with before/after images on HALCYON-1 and the `chrona init` starter.
2. Every preset renders HALCYON-1 at 1600 × 900 without `W_LAYOUT_*` or `W_SCENE_TEXT_INTERSECTION` warnings.
3. Every mechanism gap found is either filed as its own issue or attached to an existing one.

The issue's earlier images for `print-mono`, `executive-light` and `elevated-light` have output heights above 900 despite a 1600 × 900 request. Design review must distinguish requested viewport from natural overflow output and decide whether the literal criterion requires physical 1600 × 900 output or only that render input size. Do not mark row 2 met by citing a PR body alone. The starter's pre-existing as-of warning needs separate characterization; row 2 names HALCYON only.

## Baseline and dependencies to verify

- Read each PR's README, resource YAML, before/after images, changed packaged-resource test and latest check run. Confirm all five touch only their own bundle, library entry, test and research evidence; shared library/test hunks may nevertheless conflict on serial merge.
- Verify `chrona-default-draft` remains untouched (#468 ownership), Project-generic selection works on both HALCYON and the starter, and preset copy uses packaged members rather than workspace-only files.
- Verify the mechanism-gap map #476–#483 plus #466 covers all 19 numbered findings and three observations in #470. A mechanism gap must not be disguised by a YAML-specific conditional.
- Refresh current `main` and C1 CI before first merge. #466 shared-obstacle changes may alter plot-label and dependency output compared with the PR images; characterize, then update PR evidence if needed.

## Design and architecture questions

1. Are one-View/Theme/Layout-per-preset references and package resource closure sufficient to keep presets independent and project-generic? Check Specifications 06/07/08/33 and the preset catalogue contract.
2. Is the 1600 × 900 criterion about requested viewport or final SVG viewport? Document the chosen interpretation with rendered proof, not an assumption.
3. Does each preset retain source identity and semantic-role distinctions, including monochrome limitations explicitly assigned to #483? Review output rather than accepting green CI as visual proof.
4. Can the five existing PRs be merged serially without overwriting another library/test entry? Reconcile through normal follow-up commits or fresh PR heads; no force push or broad checkout.
5. Do any #466 C2/C3 changes require re-tuning these presets? If so, record the later adaptation under the owning issue, not in #470's YAML-only merge unless required to keep the published context materializable.

## Ordered, independently publishable work

1. After C1 passes, publish this design plan, then a concise integration design and whole-architecture review with the acceptance interpretation and PR dependency matrix. Publish an implementation plan listing per-PR test/evidence gates before merging.
2. Review and merge #471–#475 serially, each against the latest public `main`. Before each merge inspect exact files, conflict/mergeability and generated behavior; after each merge confirm GitHub commit/PR state and CI. Do not batch merge blindly or skip an unexpected remote update.
3. On final `main`, copy and render every preset with HALCYON and starter, collect warning diagnostics and output dimensions, inspect before/after images as a batch, and verify packaged-resource tests and public materializers. CI supplies full matrix/release gate; focused local tests suffice otherwise.
4. Publish an acceptance review with all three literal rows and direct evidence. Close #470 only if all rows are met; otherwise leave it open with exact corrective slice and owner.

This plan permits #470 integration at the #466 C1 boundary; #466 C2/C3 resumes after the independently verified preset publication unless the architecture review finds a direct dependency requiring a different order.
