<!-- chrona:literal-acceptance/v1 -->

# Implementation Review — Typed Legacy Candidate Normalization (#466 C1)

**Implementation:** `d271b175df534dd881370674c29dba4de2e0b641` on GitHub `main`. **Design:** [candidate contract](../../design/issue-466-candidate-placement-design-2026-09-26.md), [ownership correction](../../design/issue-466-candidate-normalization-ownership-correction-2026-09-26.md), [implementation plan](../../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md). **CI:** [run 36233858722](https://github.com/tya5/chrona/actions/runs/36233858722) passed all four jobs: three-OS conformance/full pytest/wheel smoke and newest-Python public reproduction.

The published C1 changes are limited to immutable candidate values, pure v0.22 rung expansion in the model, Review normalization and Layout consumption. `suppress` stays a terminal outcome. No View/Theme schema, search algorithm, obstacle policy or public resource changed. Review does not import a Layout candidate helper. Local focused Layout/Review/Scene/model tests: `229 passed`; import-direction and module-reachability checks passed; diagnostic inventory was regenerated and checked. `tools/regenerate_public_examples.py --check --jobs 4` passed for all 21 public slides. Their committed Scene/SVG bytes are unchanged. `git diff --check` passed.

## Literal issue acceptance

### Issue #466

- Source: [Issue #466](https://github.com/tya5/chrona/issues/466)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it. | met | [O2 accepted review](issue-466-shared-obstacle-prerequisite-acceptance-review-2026-09-26.md) and unchanged public check. | — |
| 2 | Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor. | not met | [C1 typed normalization](https://github.com/tya5/chrona/blob/d271b175df534dd881370674c29dba4de2e0b641/src/chrona/presentation/model/placement_candidates.py) and [test](https://github.com/tya5/chrona/blob/d271b175df534dd881370674c29dba4de2e0b641/tests/unit/chrona/presentation/model/test_placement_candidates.py) prove internal expansion and byte parity; external v0.23 declaration is still pending. | — |
| 3 | A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line. | not met | [Implementation plan](../../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md) assigns this to C2/C3. | — |
| 4 | The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used. | not met | [Implementation plan](../../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md) assigns this to C2/C3. | — |
| 5 | Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count. | deferred | [C1 typed candidates](https://github.com/tya5/chrona/blob/d271b175df534dd881370674c29dba4de2e0b641/src/chrona/presentation/model/placement_candidates.py) have identity but the new joint-trial accounting is pending. | [Implementation plan](../../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md) |
| 6 | A Theme can draw the tail and balloon outline. A Theme without it renders as today. | not met | [Implementation plan](../../planning/active/issue-466-candidate-placement-implementation-plan-2026-09-26.md) assigns Theme/Scene/adapters to C2/C3. | — |
| 7 | The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it. | not met | [Candidate design](../../design/issue-466-candidate-placement-design-2026-09-26.md) and [Spec 33](../../specification/33-intent-oriented-layout.md) describe the successor, but the complete released model is pending. | — |

## Programme-level criteria (optional)

C1 is an independent byte-preserving foundation. It is not issue #466 completion.

## Architecture conclusion

Review normalization owns old View spelling; the shared model carries immutable candidate intent; Layout still owns all geometry, text measurements, obstacles and routes. No Scene or adapter change occurred. Accept C1 only after the CI run above is green, then use its published commit as the base for #470 integration and later #466 C2/C3.
