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
[PR #1263 snapshot](https://github.com/tya5/chrona/actions/runs/37868811432),
head `77c8e092`: 149 paths audited, all 136 existing SVG/Scene files byte-identical,
four new SVG/Scene files, four report changes, no retirements. Both new SVGs
match the local rendered bytes; packaged-font raster inspection confirms
alternating months and months following their quarter's fill. The inherited
footer-overflow warning is disclosed, not absorbed by unrelated data/style edits.
Committed generated evidence and exact-main three-OS release remain pending;
keep the issue open.

## Architecture conclusion

View declares the source; Presentation resolves neutral calendar interval keys
and complete Scheme paints. Layout retains geometry and measurement ownership;
Scene applies completed paints by placement identity. Adapters add no policy.
The dedicated example Theme leaves the existing axis-tier Theme byte-identical
to the public base. No project data, defaults, preset bundles or generated files
are edited to absorb side effects.
