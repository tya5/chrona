<!-- chrona:literal-acceptance/v1 -->

# Axis band colour scales — acceptance review

## Literal issue acceptance

### Issue #490

- Source: [Issue #490](https://github.com/tya5/chrona/issues/490)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A band tier can resolve alternating fills from a Theme, and a committed slide shows it. | not met | [SVG integration tests](../../../tests/integration/test_axis_band_color_scales.py) pass; [authored slide](../../../examples/controller-z/contexts/axis-alternating.yaml) renders alternating fills. Committed generated SVG and release evidence remain pending. | — |
| 2 | A band tier can resolve a different fill per interval from a declared Theme colour scale keyed by interval, and a finer tier can key off its containing coarser interval; #421's separability check applies. | met | [Synthetic tests](../../../tests/unit/chrona/presentation/model/test_axis_color_scale.py) and [SVG integration tests](../../../tests/integration/test_axis_band_color_scales.py) cover interval mapping, later-declared parents, natural containment, missing mappings and separability warnings; [authored quarter/month slide](../../../examples/controller-z/contexts/axis-interval-scales.yaml) renders both paints. | — |

## Programme-level criteria (optional)

Implementation base: `510fd5f90bcc057d72e575423ec6e114dfa51837`;
published wiring: `9c3362aaed3a09794fb72350abe3c2b1e23fc9d9`.
Focused tests: 169 passed; the 8 SVG integration tests also pass after example
Theme isolation. S0 after isolation: 448 mapped documents, 739 probes, PASS
(L2+L3 40.1s; four existing invalid fixtures unchanged).
The two disposable SVG/Scene renders exist, but materializer comparison reports
the expected mismatch because their generated repository evidence is not yet published.
[Pre-isolation CI](https://github.com/tya5/chrona/actions/runs/37874047420),
head `50246dfd`: conformance, materializer reproduction and two pytest shards
passed. The only test failure was the packaged/example Scheme equality guard;
derived-ready failed transitively. The correction isolates the same two demo
categories in `schemes/axis-color-scales.yaml`, referenced only by the two new
Contexts. `executive-light.yaml` is restored byte-identically to ready main;
no preset bundle or test allowance changes. Both fills clear every group/row ground by at least
1.221 and 1.365 respectively (required 1.15). The two source-ledger rows record
seven axis labels and a hosted DVT. Root reran the original readability
assertions against copied-project public renders; both pass. The focused
axis-scale suite passed 72 tests. After Scheme isolation, the original preset
equality guard and SVG suite pass (nine tests); both copied-project public SVGs
are byte-identical to the inspected corrected renders, with seven labels,
hosted DVT and no resource errors. Updated-head snapshot/CI remain required.
Packaged-font raster inspection confirms alternating months and months
following their quarter's fill. The inherited footer-overflow warning is
disclosed, not absorbed by unrelated data/style edits.
Committed generated evidence and exact-main three-OS release remain pending;
keep the issue open.

## Architecture conclusion

View declares the source; Presentation resolves neutral calendar interval keys
and complete Scheme paints. Layout retains geometry and measurement ownership;
Scene applies completed paints by placement identity. Adapters add no policy.
The dedicated example Theme and Scheme leave existing resources byte-identical
to the public base. No project data, defaults, preset bundles or generated files
are edited to absorb side effects.
