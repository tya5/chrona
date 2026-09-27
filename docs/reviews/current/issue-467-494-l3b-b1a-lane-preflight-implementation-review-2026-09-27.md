<!-- chrona:literal-acceptance/v1 -->

# B1a Partial Implementation Review — Lane Preflight (#467, #494)

**Reviewed commits:** `8b7b8373` (B1a kernel) and `46e05179` (Decimal precision classification and regenerated diagnostic inventory). **Implementation amendment:** [B1a direct preflight kernel](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md). **Predecessor:** [L3b lane and route implementation amendment](../../planning/active/issue-467-494-l3b-prelayout-route-evidence-implementation-amendment-2026-09-27.md). **Status:** partial B1a accepted as a direct Layout kernel; all #467/#494 issue criteria remain deferred. This record does not support closing either issue.

## Implementation and boundary

B1a adds a direct Layout preflight kernel that returns an immutable plan, computes the finite lane-table measurement envelope, and checks seed/final inline-frame equality. The kernel is exercised directly; it does not map the Project and View projection into complete candidate bundles or connect the plan to the composer. Public lane rendering remains fail-closed at `render_review` with `E_REVIEW_LANE_ENGINE_UNAVAILABLE`. Thus B1a makes no 02 lane count, item visibility, delta, relation-routing, or public rendered-output claim.

The implementation stays within Layout ownership. It adds no View migration, Scene/adapter projection, or public lane activation. The existing automatic path remains the public path. The lane preflight module is listed as staged with the reason and removal gate until projection closure reaches B1b/B2.

## Verification evidence

- Focused lane suite: `PYTHONPATH=.:src .venv311/bin/python -m pytest tests -q -k lane` — **34 passed**, 1,471 deselected. This includes the allocator and preflight unit tests plus lane-related contract and integration tests.
- Public materializers: `PYTHONPATH=.:src .venv311/bin/python tools/regenerate_public_examples.py --check` — **PASS (28 slides)**; generated files were not written.
- Module inventory: `python tools/check_module_reachability.py` — **97 modules reachable, 2 staged, none orphaned**.
- Public guard: [`render_review.py`](../../../src/chrona/usecases/render_review.py) raises `E_REVIEW_LANE_ENGINE_UNAVAILABLE` for `rows.mode: lanes` before scheduling.
- The three focused preflight tests are in [`test_lane_preflight.py`](../../../tests/unit/chrona/presentation/layout/test_lane_preflight.py); the direct kernel is in [`lane_preflight.py`](../../../src/chrona/presentation/layout/lane_preflight.py). These prove the plan identity/chain/cell invariants, lane-table name/count envelope, and seed/final frame equality. They do not prove projection mapping or public composition.
- [CI run 36300719801](https://github.com/tya5/chrona/actions/runs/36300719801) completed **failure** on `8b7b8373`. On macOS, Ubuntu, and Windows, conformance failed on a stale diagnostic inventory and `E_LAYOUT_FLOAT_SUM_UNCLASSIFIED` in `lane_preflight.py`; pytest failed at `tests/unit/tools/test_check_layout_float_accumulation.py`. The newest-Python public-materializer reproduction passed. The exact fix at `46e05179` classifies the all-Decimal sum and regenerates the inventory. [Corrective CI run 36301362495](https://github.com/tya5/chrona/actions/runs/36301362495) passed all three OS conformance/full pytest/wheel-smoke jobs and newest-Python public-materializer reproduction. No unrelated red check remains on that commit.

## Literal issue acceptance

### Issue #467

- Source: [Issue #467](https://github.com/tya5/chrona/issues/467)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A lane row mode exists. On `02-programme-board` the 26 items occupy at most 12 lanes, with the chain `structure → avionics → bus-test` on one lane. | deferred | [B1a preflight kernel](../../../src/chrona/presentation/layout/lane_preflight.py) is direct-only; [public rendering guard](../../../src/chrona/usecases/render_review.py) keeps lane rendering fail-closed. No 02 composition exists in B1a. | [B1b/B2 implementation gate](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 2 | Every packed task and milestone has a visible name on the slide; no `W_LAYOUT_LABEL_SUPPRESSED` for a packed item on any committed slide. | deferred | [Preflight tests](../../../tests/unit/chrona/presentation/layout/test_lane_preflight.py) check a measured table envelope, not visible names in composed slides; [public rendering guard](../../../src/chrona/usecases/render_review.py) prevents lane output. | [B1b/B2 implementation gate](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 3 | Lane assignment is deterministic, and a test shows that one inserted item does not reorder unrelated lanes. | deferred | [Allocator test](../../../tests/unit/chrona/presentation/layout/test_lane_allocation.py) demonstrates deterministic insertion for the neutral allocator, but no integrated lane assignment is published. | [B1b/B2 implementation gate](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 4 | Deltas remain visible for packed items that have them. | deferred | [B1a plan contract](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) explicitly leaves projection-to-bundle mapping to B1b; [public rendering guard](../../../src/chrona/usecases/render_review.py) prevents visible packed output. | [B1b/B2 implementation gate](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |
| 5 | New Views and the packaged presets default to lanes; `automatic` still renders exactly as today. | deferred | B1a makes no View, preset, or Context migration; the [public rendering guard](../../../src/chrona/usecases/render_review.py) preserves fail-closed lane behavior. The 28-slide [corrective materializer check](https://github.com/tya5/chrona/actions/runs/36301362495) passed without generated changes. | [L3c migration and activation gate](../../planning/active/issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md) |
| 6 | At least three committed slides use lanes (for example `01`, `02` and `06`), and their evidence is reproducible. | deferred | [Public rendering guard](../../../src/chrona/usecases/render_review.py) disallows lane rendering, and no committed lane slide evidence is produced by B1a. The passing 28-slide reproduction covers current public artifacts only. | [L3c migration and activation gate](../../planning/active/issue-467-494-l3-lane-completion-publication-amendment-2026-09-27.md) |

### Issue #494

- Source: [Issue #494](https://github.com/tya5/chrona/issues/494)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `02-programme-board` (lanes), no relation is suppressed for `egress-collision`, and every remaining suppression is listed with a measured cause. | deferred | B1a has no relation-routing integration; the [public rendering guard](../../../src/chrona/usecases/render_review.py) prevents a lane route inventory. | [B3 route evidence gate](../../planning/active/issue-467-494-l3b-prelayout-route-evidence-implementation-amendment-2026-09-27.md) |
| 2 | `test_lane_relation_routes_never_cross_a_required_lane_label` still passes on 02, 11 and 12: no route crosses any lane or member label. | deferred | The [B1a implementation amendment](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) defers route integration to B3; the public lane guard yields no route output to inspect. | [B3 route evidence gate](../../planning/active/issue-467-494-l3b-prelayout-route-evidence-implementation-amendment-2026-09-27.md) |
| 3 | Lane count and lane membership on 02 are unchanged, or any change is attributed. | deferred | B1a does not compose `02-programme-board`; [the preflight module](../../../src/chrona/presentation/layout/lane_preflight.py) receives neutral candidates and cannot establish slide membership. | [B2 composition and B3 route evidence gates](../../planning/active/issue-467-l3b-candidate-footprint-implementation-amendment-2026-09-27.md) |

## Programme-level criteria (optional)

| Criterion | Disposition | Evidence |
| --- | --- | --- |
| B1a publishes only the direct immutable preflight kernel, with public lane mode fail-closed. | met for this partial slice | [Preflight implementation](../../../src/chrona/presentation/layout/lane_preflight.py), [staged-module owner/reason](../../../tools/staged_modules.txt), and [public guard](../../../src/chrona/usecases/render_review.py). |
| B1a CI/release evidence is complete. | met for this partial slice | The initial [red run 36300719801](https://github.com/tya5/chrona/actions/runs/36300719801) has an attributed B1a-only failure; [corrective run 36301362495](https://github.com/tya5/chrona/actions/runs/36301362495) passed every planned job after `46e05179`. |

## Architecture conclusion

The direct preflight kernel and immutable plan are correctly owned by Layout. The slice remains partial by design: B1b must map semantic candidates into atomic member footprints, B2 must consume one preflight plan in the content solve and composer, and B3 must supply typed route-attempt evidence. Public lane activation and preset/View migrations belong to L3c. B1a's focused tests, 28 public materializers, 97/2/0 reachability, and corrected CI all pass. Keep #467 and #494 open; neither issue has rendered-lane acceptance evidence yet.
