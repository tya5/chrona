<!-- chrona:literal-acceptance/v1 -->

# Issue #1291 — axis label containment acceptance

Product correction `94a7a88f`; diagnostic/ledger test repair `203292dc`.
The shared measurement prerequisite is on main; no redundant `text.py` change.
[Design and architecture authority](https://github.com/tya5/chrona/issues/1291#issuecomment-6093419760).
[PR #1363](https://github.com/tya5/chrona/pull/1363) snapshot `11673962707`
on `8527f852` / ready base `504f6209` accounts for all 46 Scene/SVG
pairs: 45 byte-identical; flight-readiness removes only two nonfitting month
labels (3→1), with unchanged viewport, routes and other primitives. All 411
surviving axis labels satisfy plot containment; the 357 hosted labels also
satisfy their painted-host bounds. The other 54 honestly retain no host.
All 101 before-blobs match that base; exactly five generated paths change:
the one Scene/SVG pair and inventory, contrast and font-identity reports.
Artifact SHA256: `84e5d67f54e9a708da6c705c42a1fabcfa62658f4d7bf34b264e8aea85ec4c9b`.
[CI 38062630277](https://github.com/tya5/chrona/actions/runs/38062630277)
passed all three pytest shards, conformance, MCP and newest-Python reproduction.
Three obsolete overflow/label-count assertions were corrected; independently
provoked non-axis overflow/intersection coverage remains. No corpus edit.
Repair verification: MCP tool suite 186 passed (37.39s); skill diagnostics
20 passed (5.34s); unchanged genuine annotation-rail overflow case passed in
the focused batch; ledger rules 10 passed (2.97s). The intersection fixture
uses actual Scene evaluation, warning collection and CLI stdout serialization,
not mocked findings. Main `5a03294b` adds only the #1214 acceptance document;
the ordinary refresh changes no product or generated output. The refreshed
head still requires its own PR gates/snapshot, followed by exact-main release.

## Literal issue acceptance

### Issue #1291

- Source: [Issue #1291](https://github.com/tya5/chrona/issues/1291)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test renders a window whose last band segment is narrower than its label. It asserts from the Scene that every axis-label primitive's box lies inside its band segment and inside the plot's inline extent. | met | [Synthetic Scene/SVG end-edge case](../../../tests/integration/test_axis_band_label_containment.py): surviving labels fit their own bands/plot; truncated edge is absent with the thinning diagnostic. | — |
| 2 | The same test at the plot start (window begins a few days before a quarter ends). | met | [Parameterized start-edge case](../../../tests/integration/test_axis_band_label_containment.py). | — |
| 3 | No canvas growth for this case: the SVG width equals the requested viewport inline size. | met | [Both real SVG roots](../../../tests/integration/test_axis_band_label_containment.py) remain 1600px. | — |
| 4 | Existing axis tests pass. Corpus diffs are listed in the PR. | met | Axis/text/index batch: 308 passed (32.51s); corrected native-lane batch: 91 passed (5.99s), overlapping, not summed. [CI](https://github.com/tya5/chrona/actions/runs/38062630277) passes all three shards. [PR #1363](https://github.com/tya5/chrona/pull/1363) lists the 46-pair audit: 45 identical; flight-readiness primitives 77→75 and labels 3→1; no other primitive or route changes; +2 axis-thinned/+1 density, −2 label-overflow; SVG 1920×1080 unchanged. | — |
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
refreshed-head snapshot and PR gates, and acceptance-containing exact-main
three-OS full release. Literal acceptance is not a substitute for that gate;
do not close before the exact-main run succeeds.
