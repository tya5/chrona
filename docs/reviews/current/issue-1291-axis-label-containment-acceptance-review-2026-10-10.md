<!-- chrona:literal-acceptance/v1 -->

# Issue #1291 — axis label containment acceptance

Prepared implementation `957bc641`; ordinary integration `b7af568e` includes
published main `85ff5e4460cb1827127630467efb2807513186ce` (#1318).
The shared measurement prerequisite is on main; this slice adds no redundant
`text.py` correction. Native-lane correction focused tests: 91 passed (5.99s).
[Design and architecture authority](https://github.com/tya5/chrona/issues/1291#issuecomment-6093419760).
Local evidence only; no PR, current-corpus snapshot or exact-main release yet.

## Literal issue acceptance

### Issue #1291

- Source: [Issue #1291](https://github.com/tya5/chrona/issues/1291)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test renders a window whose last band segment is narrower than its label. It asserts from the Scene that every axis-label primitive's box lies inside its band segment and inside the plot's inline extent. | met | [Synthetic Scene/SVG end-edge case](../../../tests/integration/test_axis_band_label_containment.py): surviving labels fit their own bands/plot; truncated edge is absent with the thinning diagnostic. | — |
| 2 | The same test at the plot start (window begins a few days before a quarter ends). | met | [Parameterized start-edge case](../../../tests/integration/test_axis_band_label_containment.py). | — |
| 3 | No canvas growth for this case: the SVG width equals the requested viewport inline size. | met | [Both real SVG roots](../../../tests/integration/test_axis_band_label_containment.py) remain 1600px. | — |
| 4 | Existing axis tests pass. Corpus diffs are listed in the PR. | not met | [Axis/index/geometry/text/Scene/edge/font/transform batch](../../../tests/integration/test_axis_band_label_containment.py): 308 passed (32.51s) on `9a00b3d3`; corrected edge/index/geometry/secondary batch: 91 passed (5.99s), including both same-unit lanes and inline-gap regression (overlapping tests, not summed). Fresh whole-corpus PR diff is still required. | — |
| 5 | Do not edit `examples/**`. | met | [Implementation](https://github.com/tya5/chrona/issues/1291#issuecomment-6093419760) owns Layout, synthetic tests and Spec50 only; adopted reviewer/bot outputs are not authored changes. | — |

## Programme-level criteria (optional)

None; the literal rows and release gates control closure.

Independent review findings addressed before this checkpoint: containment
decisions name `axis-cell-containment`; indexed native-band lookup agrees with
exhaustive paint/emission ordering and a 1,000-cell test bounds lookup to at most
12 bounds reads. [Geometry tests](../../../tests/unit/chrona/presentation/layout/test_surface_axis_tier_geometry.py)
cover secondary omission, no false visible target, unpainted hosts, rotation and
candidate-summary parity. [Shared text tests](../../../tests/unit/chrona/presentation/layout/test_text.py)
prove transformed asymmetric glyph bounds, multiline text and one compression.

Final review reproduced a defect with equal quarter intervals in separate block
lanes: a global exact-interval winner suppressed the fitting upper tier. Spec50
and the issue plan were clarified and published before the correction. Exact
interval candidates now select by primary block centre and paint/emission order;
inline gaps still constrain admission. Both label tiers survive with their own
host identities; candidate summary and final placement agree.

Current integration preserves resolved font-family identity, declared transforms
on original source lines, small-caps per-run metrics and once-only compression;
the merged asymmetric text tests retain both regression sets. No layer change.
The adjacent #1294 long-window cadence/unit policy remains a separate issue,
not a prerequisite for this boundary fix. Release still requires the
current-corpus snapshot/count audit,
exact-head PR gates and acceptance-containing exact-main full release. Do not close.
