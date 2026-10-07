<!-- chrona:literal-acceptance/v1 -->

# Release Review — Title Card core knobs

Published baseline: `a4877222d866566b640eb12b5a6963ef32b5568b`.
Core PRs [1196](https://github.com/tya5/chrona/pull/1196), [1197](https://github.com/tya5/chrona/pull/1197), and [1195](https://github.com/tya5/chrona/pull/1195) are merged. Their exact implementation releases passed: [1189](https://github.com/tya5/chrona/actions/runs/37553870166), [1190](https://github.com/tya5/chrona/actions/runs/37560715558), [1191](https://github.com/tya5/chrona/actions/runs/37544843273).
Reviewer adoption is [PR 1200](https://github.com/tya5/chrona/pull/1200), independently checked in the published [Scene][scene] and actual [SVG][svg], not inferred from the PR description.

## Literal issue acceptance

### Issue #1189

- Source: [Issue #1189](https://github.com/tya5/chrona/issues/1189)
- Observed: 2026-10-07

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With a kicker, three Text runs stack in order inside the heading slot, each in its own role. | met | [Actual SVG tests](https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_heading_kicker.py); published [SVG][svg]: kicker 24px, title 60px, deck 12px, in order. | — |
| 2 | The block's measured size includes the kicker. | met | [Envelope tests](https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_heading_kicker.py); published [Scene][scene] title slot y=28..158.1 contains all three runs. | — |
| 3 | Without a kicker, the output is byte-identical. | met | [Unused/absent declaration tests][kicker-tests]; [final PR CI](https://github.com/tya5/chrona/actions/runs/37550196781), artifact11452657463: 65 SVG + 65 Scene unchanged against e711e3ad. | — |
| 4 | Title Card adopts `第弐面`. | met | [PR 1200](https://github.com/tya5/chrona/pull/1200); [SVG][svg] kicker baseline (28,57.64), above title/deck, inside measured slot. | — |

### Issue #1190

- Source: [Issue #1190](https://github.com/tya5/chrona/issues/1190)
- Observed: 2026-10-07

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `inline` puts the three runs on a shared baseline in order, with the declared gaps. | met | [Actual SVG tests](https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_summary_inline.py); published [SVG][svg] baseline y=105.16, x=1130/1236/1298.864, measured gaps 10px/10px. | — |
| 2 | `stack` is byte-identical. | met | [Absent/explicit-stack tests][inline-tests]; [final PR CI](https://github.com/tya5/chrona/actions/runs/37557075348), artifact11455282947: 65 SVG + 65 Scene unchanged against 983b07d3. | — |
| 3 | Each run takes its role's typography and ink. | met | [Distinct typography/paint tests](https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_summary_inline.py); [Scene][scene]/[SVG][svg] caption/value/unit roles, font sizes 24/56/20px. | — |
| 4 | Title Card adopts `発射まで 63 DAYS`. | met | [PR 1200](https://github.com/tya5/chrona/pull/1200); all three strings in the published [SVG][svg], with one baseline and declared gaps. | — |

### Issue #1191

- Source: [Issue #1191](https://github.com/tya5/chrona/issues/1191)
- Observed: 2026-10-07

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `fill` makes the bar's inline extent equal the container's inner width. | met | [Fill/hug and stamp-inset tests](https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_annotation_kind_header.py); [Scene][scene]/[SVG][svg] bars fill the completed text lane after border/inset/stamp reservations. | — |
| 2 | A heading line sits between the bar and the body, in its own role, and the container grows to fit it. | met | [Separate-heading growth/ground tests](https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_annotation_kind_header.py); [SVG][svg] three 15px annotation-heading runs between kind bar and 12.5px body. | — |
| 3 | The defaults are byte-identical. New declarations must not change output for existing YAML that does not opt in. | met | [Absent/explicit-fill tests][kind-tests]; [final PR CI](https://github.com/tya5/chrona/actions/runs/37540857878), artifact11449410619: 65 SVG + 65 Scene unchanged against 131971f8. | — |
| 4 | Title Card adopts both. | met | [PR 1200](https://github.com/tya5/chrona/pull/1200); all three filled Rect bars and separate headings match [Scene][scene] in actual [SVG][svg]. | — |

## Programme-level criteria (optional)

All 15 adoption elements were checked: 12 text baselines and 3 bar rectangles match SVG/Scene within 0.001px. Core snapshots add no diagnostic codes; only expected diagnostic/coverage reports change. No corpus edits in this review.
Fresh baseline check: heading-kicker, summary-inline, annotation-kind-header integration suites and literal-review validator unit tests: 65 passed (60.46s); literal-review structural check passed.
Required closure gate: the three-OS pytest/conformance/wheel/materializer run on the exact published commit containing this review; closing comments must cite that receipt.

## Architecture conclusion

View/content owns text and identity, Theme supplies intent, Layout owns measured envelopes/baselines/placement, Scene projects completed geometry, adapters serialize it. Specifications 06/07/08/25/33/43/49/56 remain aligned.
The separate larger-heading rail-placement defect is [#1201](https://github.com/tya5/chrona/issues/1201), first next in lane G. This review verifies current 15px adoption, not the desired 22px rail behavior or overall Title Card sign-off (#1182).

[scene]: https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/examples/halcyon-1/generated/23-titlecard.scene.json
[svg]: https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/examples/halcyon-1/generated/23-titlecard.svg
[kicker-tests]: https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_heading_kicker.py
[inline-tests]: https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_summary_inline.py
[kind-tests]: https://github.com/tya5/chrona/blob/a4877222d866566b640eb12b5a6963ef32b5568b/tests/integration/test_annotation_kind_header.py
