# Acceptance Review — Five Catalogue Presets (#470)

**Design authority:** [correction](../../design/issue-470-catalogue-preset-integration-correction-2026-09-26.md) and [implementation amendment](../../planning/active/issue-470-catalogue-preset-integration-implementation-amendment-2026-09-26.md). **Merge:** [PR #485](https://github.com/tya5/chrona/pull/485) at `ea8c2d1877589c83188573391443e5cfc7695370`. **Research wording correction:** `5b2d5863b03a2dde67ef6b45b0190ce040036e95`.

## Verification on public main

The combined PR contained only five preset bundles, library references, a
sorted packaged-resource test union and their research images/READMEs; it
did not change mechanism, schema, the bare default, or corpus resources. The
current-base synthetic merge was conflict-free. After the real merge, all five
presets were copied via `chrona preset copy <id>` from public `main` and used
to render HALCYON-1 with `examples/halcyon-1/actual.yaml` at requested
`--viewport 1600x900`, plus a fresh `chrona init` starter. Each produced SVG
and an emitted Scene. HALCYON CLI was quiet in all five cases. The starter
retained its characterized as-of `W_LAYOUT_LABEL_OVERFLOW`, outside row 2's
HALCYON scope. `elevated-light` additionally rendered under the v0.7 PNG
profile; the PNG and all five research before/after pairs were inspected.

| Preset | Actual HALCYON canvas | Scene diagnostics | Layout failures |
| --- | --- | --- | ---: |
| `mission-light` | 1600 × 1152 | incomplete TVAC ×1; declared label suppression ×2 | 0 |
| `control-room-dark` | 1600 × 1152 | incomplete TVAC ×1; declared label suppression ×2 | 0 |
| `print-mono` | 1600 × 1111 | incomplete TVAC ×1; declared label suppression ×1 | 0 |
| `executive-light` | 1600 × 1376 | incomplete TVAC ×1; declared label suppression ×1 | 0 |
| `elevated-light` | 1600 × 1376 | incomplete TVAC ×1; declared label suppression ×1 | 0 |

The failure count filters both Scene and CLI evidence for
`W_LAYOUT_*OVERFLOW*`, `W_LAYOUT_ROW_DENSITY` and
`W_SCENE_TEXT_INTERSECTION`; none occurred on HALCYON. TVAC's incomplete
observation and declared plot-label suppression were not hidden. The research
READMEs now say “no CLI warnings or layout failures” and name the Scene facts,
instead of the ambiguous “no warnings”. The unchanged limitations are owned
by #466 and #476–#483; they are not represented as solved by YAML.

- Current-base and post-merge `tests/integration/test_packaged_resources.py`:
  **6 passed** each time.
- Current-base and post-merge
  `tools/regenerate_public_examples.py --check --jobs 4`: **21 public slides
  pass**, no committed Scene/SVG byte change.
- Post-merge [CI run 36235696291](https://github.com/tya5/chrona/actions/runs/36235696291):
  all three OS conformance/full pytest/wheel-smoke jobs and newest-Python
  materializer reproduction succeeded.

## Literal issue acceptance

| Criterion | Status | Direct evidence |
| --- | --- | --- |
| Each of five presets has its own members and a merged tuning PR with before/after images on HALCYON-1 and starter. | met | #485 merge `ea8c2d18`; distinct `presets/bundles/<id>/{view,theme,layout}.yaml`, five `library.yaml` references, 15 packaged entries, research image pairs under `docs/research/presentation/preset-tuning/<id>/`. |
| Every preset renders HALCYON-1 at requested 1600 × 900, natural growth allowed, without a layout failure in CLI or Scene diagnostics. | met | Post-merge copied-preset SVG/Scene batch above: five successful renders, actual dimensions and complete diagnostic inventory, zero named failures. |
| Every mechanism gap found is separately filed or attached. | met | #470's 19-item/three-observation map to #466 and #476–#483; no mechanism claim or silent workaround was added by #485. |

All literal criteria are met. The issue owner stated that a separate
post-review follows the merge. Leave #470 open until that reviewer disposition
is recorded; this review does not impersonate the owner or auto-close the
reviewer-maintained board.
