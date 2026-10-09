<!-- chrona:literal-acceptance/v1 -->

# Issue #849 — ordered pattern circles

Implementation: `84371c27e2b7f8f7ecc427da842d1244c4d387d9`.
[Completed design, architecture review and implementation plan](../planning/issue-849-pattern-occlusion-2026-10-09.md).
Source/catalogue successors migrate atomically; the nine archived originals
are byte-identical. Layout owns completed phase/clip, Scene transports circle
channels and widths, SVG serializes native circles. Opaque contrast stays
conservative; fill-less patterns reject substrate before Scene completion.

## Literal issue acceptance

### Issue #849

- Source: [Issue #849](https://github.com/tya5/chrona/issues/849)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A seigaiha tile is expressible without approximation, and the density and contrast gates see the occluded result. | met | [Independent nine-circle sample oracle](../../../tests/unit/chrona/presentation/icons/test_normalizer.py): 4270/16384 visible samples, 2606bp; ordered erasers, restored ink, thin annuli and clipping. [Actual pipeline and both observers](../../../tests/integration/test_seigaiha_acceptance.py) verify final density and exact native SVG; [sparse contact](../../../tests/unit/chrona/presentation/scene/test_pattern_ink.py) and [pre-Scene refusal](../../../tests/unit/chrona/presentation/scene/test_v05_builder.py) cover the other admitted paint path. | — |
| 2 | Evidence: Yuya's launch window through YAML. | met | [Yuya Theme](../../../examples/halcyon-1/themes/yuya.yaml), [pinned Context](../../../examples/halcyon-1/contexts/22-yuya.yaml) and [successor source](../../../src/chrona/resources/icons/chrona-target-parts-v2026-10-09.source.yaml) emit the exact 20×10 nine-circle stack in the pipeline test. Actual SVG and packaged-font PNG inspected locally. The existing substrate/ground equality warning (ratio 1.0, floor 1.1) remains disclosed; ink contrast is 3.597:1. No unrelated target tuning. | — |

## Programme-level criteria (optional)

Focused runs passed: normalizer 34, Layout/Scene/paint/SVG 215, contract/shared
graphics 116, resource/schema 152, package/library 17 and actual-Yuya checks.
S0 passed: 443 mapped documents, 739 probes, L2+L3 39.6s, four existing invalid
fixtures unchanged; successor and additive Scene deltas are explicit.
Schema inventory/annotations/references and Scene delivery checks passed.
No manifest-derived output was edited. [Exact-head PR run 37882016501](https://github.com/tya5/chrona/actions/runs/37882016501)
passed on `8fba4b2d`, ready base `e52e9c31`. Artifact 11595342434,
digest `sha256:fdd886deaff471170bfdbf4a1b00095bbfd114397c113bf4666f7e62bf9df374`:
149 paths, 23 changed (11 SVG, 11 Scene, inventory), no additions/retirements.
Ten non-Yuya Scenes change only provenance; their SVGs change only pattern IDs.
Yuya alone changes completed pattern content: nine native circles, density 2606bp.
Both #490 SVG/Scene pairs remain byte-identical; bare-site counts stay 10/76/5.
[Independent artifact audit](https://github.com/tya5/chrona/issues/849#issuecomment-6074159632).
Combined axis/pattern tests: 129 passed (28.25s); schema-management tests: 189 passed.
Final S0: 451 mapped documents/739 probes, PASS (44.9s); four invalid fixtures
unchanged and both #490 materializer byte checks passed. No baseline was relaxed.

PR #1265 merged at `02ad1ecb`; bot main `8faae268aa005d253dfc88100f0879dae372e697`
matches all 149 audited snapshot paths. Trusted gate 37885200009 and sync 37884422454
passed. [Exact-main release 37886024726](https://github.com/tya5/chrona/actions/runs/37886024726)
passed macOS/Ubuntu/Windows full pytest (8354/8350/8349 passed, 67/71/72 OS-dependent
skips), conformance and installed-wheel smoke, MCP-floor and newest-Python public
reproduction. [All-row closing audit](https://github.com/tya5/chrona/issues/849#issuecomment-6075135029):
closed 2026-10-09T05:48:25Z; no deferred criterion.
