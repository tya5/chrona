<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Painted-Surface Contrast (#459)

**Implementation:** [`16162723`](https://github.com/tya5/chrona/commit/161627237f7d83875b755de8f3e595d52ada64b6).
**Plan:** [implementation plan](../../planning/active/issue-459-surface-contrast-implementation-plan-2026-09-26.md).
**Design:** [selected contract](../../design/issue-459-surface-aware-contrast-design-2026-09-26.md)
and its linked corrections.

## Literal issue acceptance

### Issue #459

- Source: [Issue #459](https://github.com/tya5/chrona/issues/459)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `variance-behind` text is held to 4.5:1 and meets it on every committed slide. | met | [Contrast report](../../diagnostics/presentation-contrast.md): both finish-delta and table-cell rows are `required`, floor 4.500, minima 5.461 and 5.438, zero errors. Theme closure rejects de-emphasis. | — |
| 2 | Mark roles have a floor, and every committed planned bar meets it against the surface it is drawn on. | met | [Contrast report](../../diagnostics/presentation-contrast.md): planned mark floor 3.000, 206 bars on 19 slides, minimum 9.223, zero errors. The report names the paint-ordered ground for each bar. | — |
| 3 | The contrast report states, for each primitive, the ground it was measured against. | met | [Per-primitive grounds](../../diagnostics/presentation-contrast.md#per-primitive-grounds) list Scene, primitive, sample point, ground identity/kind/colour, measured fill or stroke channel, ratio and floor. | — |

## Programme-level criteria (optional)

No additional programme criteria.

## Verification and generated evidence

- The public materializer byte-reproduction test passed for all 21 committed contexts. All 21 Scene/SVG pairs were regenerated with their resource changes; Scene non-paint fields and SVG root viewports were unchanged in the batch diff. The generated evidence also updated the diagnostic inventory and derived Aster Theme pins.
- Focused policy, Scheme and report tests passed (14 tests), including panel overlap, canvas fallback, gradient sampling, stroke-edge ground, hosted progress fill and per-primitive report output.
- `python conformance/run_conformance.py` passed, including documented commands, public contrast, schema/diagnostic inventories, and reachability checks. `tools/check_svg_explicit_fill.py` passed for 21 SVGs. `git diff --check` passed.
- Raster review of the HALCYON monochrome gallery and controller elevated-gradient slide confirmed planned marks remain visibly delineated. The closed-day stroke was returned to the neutral decoration token after the first raster pass made the monochrome slide too dense.
- The first [CI run](https://github.com/tya5/chrona/actions/runs/36217597562) reproduced all public contexts and passed conformance, but pytest found two existing CLI warning test doubles missing the newly required Scene field on every OS. The [test correction](https://github.com/tya5/chrona/commit/6246fc2a6c6bc7db843bc165684eda31f573789e) makes the doubles represent a complete render result and adds direct tabular-warning coverage. The [final CI run](https://github.com/tya5/chrona/actions/runs/36217779916) passed macOS, Ubuntu and Windows conformance/full pytest/wheel jobs and newest-Python public-materializer reproduction.

## Architecture conclusion

The semantic registry classifies marks; the Theme and Scheme own their paint choices. Scene contrast analysis inspects completed primitive paint order and reports the actual channel-specific ground. It does not relocate placement or routing out of Layout, nor alter Scene/adapters' rendering contract. Opaque linear gradients are sampled deterministically; unsupported underlays fail explicitly rather than being credited with canvas contrast. No unresolved design gap is accepted.
