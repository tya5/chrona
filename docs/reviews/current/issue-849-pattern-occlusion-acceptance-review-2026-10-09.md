<!-- chrona:literal-acceptance/v1 -->

# Issue #849 — ordered pattern circles

Implementation: `84371c27e2b7f8f7ecc427da842d1244c4d387d9`.
[Current design, architecture review and implementation plan](../../planning/active/issue-849-pattern-occlusion-2026-10-09.md).
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
No manifest-derived output was edited. Definition-ID changes may be nonvisual;
the Yuya pattern/closure change is intended. Required PR snapshot batch audit,
conformance/pytest/newest-Python and exact-main three-OS release containing this
review remain pending. Local evidence is not release acceptance; keep #849 open.
