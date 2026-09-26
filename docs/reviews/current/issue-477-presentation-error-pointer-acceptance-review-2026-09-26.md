# Acceptance Review — Presentation Error Pointer Transport (#477)

**Code:** `fdffec0e650417e897c6ccd15c52482bd938ab68`.
**Generated inventory correction:** `c9fb053a7d9b3d942f80c05b74214a6f533b0eba`.
**Material CI:** [run 36235268552](https://github.com/tya5/chrona/actions/runs/36235268552), all three OS conformance/full pytest/wheel-smoke jobs and newest-Python public reproduction successful.

## Verification and architecture

`render_review` now has one typed presentation-error transport boundary.
Detector code, detail and pointer survive as `RenderFailed`, then as CLI
`sourceRef`. The solver-local duplicate adapter was removed. Ingress aggregate,
Scene-build, font, closure and renderer paths remain distinct. No schema,
resource, Theme requirement, geometry, Scene or adapter behavior changed.

- `.venv311/bin/python -m pytest -q tests/cli/test_cli.py tests/unit/chrona/usecases/test_render_review.py`: **86 passed**.
- `.venv311/bin/python tools/regenerate_public_examples.py --check --jobs 4`: **21 public slides pass**, no generated Scene/SVG byte change.
- `.venv311/bin/python tools/diagnostic_inventory.py --check`: pass after the generated source-location inventory was refreshed.
- The first CI run, [36234981635](https://github.com/tya5/chrona/actions/runs/36234981635), had all 3 OS conformance jobs fail only at `E_DIAGNOSTIC_INVENTORY_STALE`; pytest itself passed. The inventory correction was published as `c9fb053a`, and the subsequent four-job CI passed. The earlier red run is not treated as acceptance.

## Literal issue acceptance

| Criterion | Status | Direct evidence |
| --- | --- | --- |
| Every presentation-layer error carrying a pointer reaches CLI `sourceRef`; known `LayoutError`, `ThemeTokenError`, `ScenePaintError`. | met | The use-case test injects all three typed exceptions and verifies exact `RenderFailed.source_ref`; the CLI's existing adapter serializes that field, and both real CLI tests below verify end-to-end output. The single outer catch covers measurement, layout and Scene paths. |
| CLI render without `timeline.groupHeader.blockSize` under header grouping reports `/body/metrics/timeline.groupHeader.blockSize`. | met | `test_cli_render_keeps_detector_owned_theme_pointer[group-header-metric-…]` copies the header-grouped Controller Z View, removes only that Theme metric and checks exact code/component/pointer with no artifact. |
| CLI render without `roles.numeric` with a `Δ` column reports the role pointer. | met | The same parametrized CLI test adds a signed-day `Δ` column to Controller Z, verifies the Theme has no numeric role, and checks `/body/roles/numeric/fontFamily` with no artifact. |

No criterion is deferred. #477 may close. #470's combined preset merge uses
this accepted public base; #466's unrelated untracked schema draft is not
included in the commits or this acceptance.
