<!-- chrona:literal-acceptance/v1 -->

# Executive summary acceptance review

## Literal issue acceptance

### Issue #1700

- Source: [Issue #1700](https://github.com/tya5/chrona/issues/1700)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic: a depth-1 rollup with nested gates keeps the gates (or emits a pointed diagnostic naming them), and draws exactly one summary mark per group. | met | [Depth0/1/all and Snapshot Model cases](../../../tests/unit/chrona/presentation/model/test_projection_rows.py); [native overlapping-date gates, separate bands, labels, comparison and relation-port tests](../../../tests/integration/test_first_run_hierarchy.py); [clipped primary-summary geometry](../../../tests/unit/chrona/presentation/layout/test_surface_window_marks.py). | — |
| 2 | A guide section shows a one-page executive summary from an imported CSV. It runs in the docs tests and renders with at least default, executive-light and mission-light. | met | [Guide](../../guides/executive-summary.md) and [executed literal commands](../../../tests/integration/test_executive_summary_guide.py); all three native SVGs contain both full gate captions. Mission-light uses its bundled preset with a documented project-local Layout override, not a modified shipped preset. | — |
| 3 | A count table and PNGs. | met | [Pinned before/after counts, five inspected PNGs and exact inputs](https://github.com/tya5/chrona/tree/7e91d0f2619bb49319f9e47b1c6b49ed596067d1/review-evidence/issue-1700), source `f172dfb0be65fd01d650bd166b3e85e2cb761d08`. Default previously rejected before producing a PNG. | — |

## Programme-level criteria (optional)

Release pending: final-base PR CI and exact-main three-OS release remain required.
Focused projection/Layout/Scene/native/docs tests pass181; no local full pytest
or whole-materializer sweep was duplicated. Official snapshot
[12133549157 / source70a8a2faa](https://github.com/tya5/chrona/actions/runs/39119974142)
was compared across all109 payloads: eight paths change (two Scene/SVG pairs
and four reports). Flight-readiness75→74 and replan-baseline144→143 each remove
one overlay, add0 and change0 retained primitives. Labels29/48, Paths15/37,
warnings417 and errors0 remain unchanged. All four native before/after public
SVG rasterizations were inspected; no generated files or test assertions were
hand-edited. Newest-Python public reproduction and PR conformance pass on that
source. The final-base run follows the separate typed-fields docs merge.

[Pre-code design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1700#issuecomment-6248519700)
and normative correction `bba2cf919` precede code `05695184a`.
Model closes retained membership without changing Core ancestry or inferring
attachments; ordinary track policies are preserved, not forced to shared.
Layout owns completed marks, clipping, fitting and routes. Removing the duplicate
shape does not remove comparison facts or the primary relation host. Scene and
adapters acquire no hierarchy or placement responsibility. Specs06/38 record
the intended depth/overlay migration; no schema or corpus-resource adaptation.
