<!-- chrona:literal-acceptance/v1 -->

# Release Review — Coherent Draft Allocation and Starter Gate (#468)

**Design plan:** [plan](../../planning/active/issue-468-draft-allocation-and-perceptibility-design-plan-2026-09-26.md).
**Design and architecture:** [design](../../design/issue-468-coherent-draft-allocation-design-2026-09-26.md),
[review](issue-468-coherent-draft-allocation-architecture-review-2026-09-26.md),
[fixed-host correction](../../design/issue-468-fixed-host-allocation-correction-2026-09-26.md),
and [correction review](issue-468-fixed-host-allocation-correction-review-2026-09-26.md).
**Implementation plan:** [three slices](../../planning/active/issue-468-coherent-draft-allocation-implementation-plan-2026-09-26.md).

## Literal issue acceptance

### Issue #468

- Source: [Issue #468](https://github.com/tya5/chrona/issues/468)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona render examples/halcyon-1/project.yaml` with no flags emits no `W_LAYOUT_MARK_OVERFLOW`, `W_LAYOUT_ROW_DENSITY` or `W_SCENE_TEXT_INTERSECTION`. | met | [CLI test](../../../tests/cli/test_cli.py) runs the bundled project with only required output/Scene paths, checks stderr for all three codes, and checks serialized Scene and SVG. Actual bare render yielded no stderr, 1600 × 1122 SVG and legible raster. | — |
| 2 | With an explicit `--viewport 1600x900` on the same project, overflowing rows stay inside the `timeline` and `table` slots or grow them together; no note is overprinted. A test covers this. | met | [CLI test](../../../tests/cli/test_cli.py) runs explicit 1600x900 and checks row containment, table/timeline common end, notes below, and no text intersections; [render integration test](../../../tests/integration/test_render.py) also checks cell bounds and warnings. | — |
| 3 | The default draft render shows month labels on the timeline. | met | [Bundled View](../../../examples/halcyon-1/views/default-draft.yaml) declares month and quarter tiers; [CLI test](../../../tests/cli/test_cli.py) checks `Mar` in actual emitted SVG. Raster inspection confirmed the axis is visible. | — |
| 4 | The Scene perceptibility gate (#446) or an equivalent check fails when a text primitive intersects another one in a committed or starter render. | met | [Starter gate](../../../tools/check_starter_perceptibility.py) renders the real bundled Draft through Layout/Scene and runs the one #446 evaluator in [conformance](../../../conformance/run_conformance.py). [Negative test](../../../tests/unit/tools/test_check_starter_perceptibility.py) injects colliding text bounds and verifies nonzero exit with `E_SCENE_TEXT_INTERSECTION`. | — |

## Programme-level criteria (optional)

No additional programme criteria apply. The review covers all four literal
acceptance items without narrowing or deferral.

## Verification and artifact review

- I468-1 `b440ae5f42b22a360e8dbb3e31bfdcc3d88ea1c7`: focused 45 passed, conformance passed, all 21 public materializers byte-identical; [CI](https://github.com/tya5/chrona/actions/runs/36221442204) passed on three OSes plus newest-Python materializers.
- I468-2 `f78a91526fde7377dd86e66b59cb1015d84abc16`: focused CLI/Draft/integration 102 passed, conformance passed, all 21 public materializers byte-identical; [CI](https://github.com/tya5/chrona/actions/runs/36221764185) passed on three OSes plus newest-Python materializers.
- I468-3 `deb5462ee434a791ce239b20b0021f63ea2a7609`: focused gate and runner tests 10 passed, direct starter gate passed, conformance passed, all 21 public materializers byte-identical; [CI](https://github.com/tya5/chrona/actions/runs/36221992450) passed on three OSes plus newest-Python materializers.
- The actual bare project SVG and PNG were inspected together: month labels are visible; rows remain within the table/timeline region; notes are below; no text overprint. No committed public Scene/SVG materializer byte changed in the three implementation slices.

## Architecture conclusion

Layout owns the content-derived allocation and keeps fixed/capped-host fallbacks truthful. Draft ingress selects the auto-block default; the View resource declares axis semantics; Scene and adapters consume completed placement without new sizing or overlap exceptions. The starter gate reuses the existing Scene evaluator, so there is one intersection rule. The fixed-host design correction was published before implementation resumed. All four literal criteria are met; closure awaits the corrected review commit's release CI gate.
