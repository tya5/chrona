<!-- chrona:literal-acceptance/v1 -->

# Axis band colour scales — acceptance review

## Literal issue acceptance

### Issue #490

- Source: [Issue #490](https://github.com/tya5/chrona/issues/490)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A band tier can resolve alternating fills from a Theme, and a committed slide shows it. | met | [SVG integration tests](../../../tests/integration/test_axis_band_color_scales.py), [authored slide](../../../examples/controller-z/contexts/axis-alternating.yaml) and [bot-committed SVG](https://github.com/tya5/chrona/blob/e52e9c31bbb08e6e55d4389f645a04a8d5102a42/examples/controller-z/generated/axis-alternating.svg) show alternating fills. Committed bytes match the inspected PR snapshot. | — |
| 2 | A band tier can resolve a different fill per interval from a declared Theme colour scale keyed by interval, and a finer tier can key off its containing coarser interval; #421's separability check applies. | met | [Synthetic tests](../../../tests/unit/chrona/presentation/model/test_axis_color_scale.py) and [SVG integration tests](../../../tests/integration/test_axis_band_color_scales.py) cover interval mapping, later-declared parents, natural containment, missing mappings and separability warnings; [authored quarter/month slide](../../../examples/controller-z/contexts/axis-interval-scales.yaml) renders both paints. | — |

## Programme-level criteria (optional)

Implementation base: `510fd5f90bcc057d72e575423ec6e114dfa51837`;
published wiring: `9c3362aaed3a09794fb72350abe3c2b1e23fc9d9`.
Focused tests: 169 passed; the 8 SVG integration tests also pass after example
Theme isolation. S0 after isolation: 448 mapped documents, 739 probes, PASS
(L2+L3 40.1s; four existing invalid fixtures unchanged).
[PR #1263](https://github.com/tya5/chrona/pull/1263) merged at `3d7b3051` after
[exact-head CI 37878114689](https://github.com/tya5/chrona/actions/runs/37878114689)
passed every required check. Artifact `11593876282`, digest
`sha256:55c1a7f1de855f868187db25f55e9f8eda571f5660e63edd97e9de2848c4c180`:
145→149 paths, exactly two SVG/Scene pairs added; all 136 existing visual files
byte-identical. The bot commit `e52e9c31` matches all 149 audited snapshot paths.

The dedicated Scheme affects only the two new Contexts; executive-light remains
byte-identical, with no preset or test allowance changes. Original preset equality
and SVG suite: nine passed. Both inspected public renders show seven axis labels
and a hosted DVT, with no resource errors. Worst separability is 1.221/1.365
(floor 1.15); months follow their quarter's fill. The inherited footer-overflow
warning remains disclosed. PR #1265 published the completed review at `02ad1ecb`.
[Exact-main release 37886024726](https://github.com/tya5/chrona/actions/runs/37886024726)
passed on `8faae268aa005d253dfc88100f0879dae372e697`: macOS/Ubuntu/Windows full pytest
(8354/8350/8349 passed), conformance and installed-wheel smoke, MCP-floor and
newest-Python public reproduction. All 149 bot paths match the audited snapshot;
both axis pairs remain unchanged by #849. [All-row closing audit](https://github.com/tya5/chrona/issues/490#issuecomment-6075135622):
closed 2026-10-09T05:48:28Z; no deferred criterion.

## Architecture conclusion

View declares the source; Presentation resolves neutral calendar interval keys
and complete Scheme paints. Layout retains geometry and measurement ownership;
Scene applies completed paints by placement identity. Adapters add no policy.
The dedicated example Theme and Scheme leave existing resources byte-identical
to the public base. No project data, defaults, preset bundles or generated files
are edited to absorb side effects.
