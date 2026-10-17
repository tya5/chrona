<!-- chrona:literal-acceptance/v1 -->

# Issue #1608 — conditional heading parts

Heading source `fba7e5147`, face-closure correction `40380c7c1`, whole-title
omission completion `57d3e3d98`, reconciled
with ready base `3e79f971a`. Integrated product head `bf41f0a22` passed
[all PR checks](https://github.com/tya5/chrona/actions/runs/38979632628).
[Design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1608#issuecomment-6225977074)
and [frozen shared-schema integration](https://github.com/tya5/chrona/issues/1608#issuecomment-6226005448).
Ingress validates typed parts; Layout binds raw guards before measurement and
includes their late-count dependencies. No Scene or adapter policy is added.
The reviewer [accepted all three shared-design YAML declarations and disclosed
public deltas](https://github.com/tya5/chrona/pull/1621#issuecomment-6226945825).
The [integration correction](https://github.com/tya5/chrona/issues/1608#issuecomment-6226118452)
shares existing Layout fallback-run completion with measured sources and carries
those facts through independent heading and network projections. It changes no
geometry or Latin-only serialization. [Synthetic controls](../../../tests/integration/test_heading_face_closure.py)
verify the exact Japanese/Latin run identities and widths, whole/split heading
equivalence, and both network title/node producers. No fallback is selected by
Scene or an adapter.

## Literal issue acceptance

### Issue #1608

- Source: [Issue #1608](https://github.com/tya5/chrona/issues/1608)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: a part with `omitWhenZero` is drawn at 1 and omitted at 0, and an unknown figure id is the existing figure diagnostic. | met | [Synthetic controls](../../../tests/integration/test_heading_omit_when_zero.py): all three members under whole/split heading at 0/1, no blank title placeholder, remaining member identity, premeasurement omission, literal concatenation, unknown/non-count/group-scope guards and deferred guard-only reads at 0/3. Twenty tests pass. | — |
| 2 | `--preset sunday`, `marquee` and `titlecard` on `examples/chrona-roadmap` (no groups) show no zero count, viewed as PNG. The #1582 CSV still shows `in three panels`. | met | Root rendered and viewed all four PNGs using the unchanged [roadmap Project](../../../examples/chrona-roadmap/project.yaml) and public [CSV fixture](https://github.com/tya5/chrona/issues/1582): no panels/acts/sections zero phrase remains; Sunday CSV retains `in three panels`. Local artifacts `/private/tmp/chrona-1608-visual-20261017/{roadmap-sunday,roadmap-marquee,roadmap-titlecard,csv-sunday}.png`. | — |
| 3 | Public SVG/Scene changes are listed with counts. | met | Final [artifact12080406895](https://github.com/tya5/chrona/actions/runs/38979632628/artifacts/12080406895): 109 before/after paths, none added/retired. All 50 SVGs and 44 Scenes are byte-identical. The three roadmap and three HALCYON Sunday/Marquee/Titlecard Scenes each change only `/provenance/resources[3]/contentIdentity`: zero primitive, label, route, geometry or Scene-diagnostic changes per output. Diagnostics inventory alone updates validator/source references (44 lines removed, 51 added). [PR #1621](https://github.com/tya5/chrona/pull/1621) lists the counts; no generated evidence is authored. | — |

## Programme-level criteria (optional)

Validation: 46 heading/count/closure integrations and all twenty final zero-guard
controls passed. Legacy heading/contracts/count-format/content: 239 passed;
shared-schema/inventory: 147 passed. Face-closure integration: 67 passed;
Layout text/heading: 76 passed; final network/title/omission batch: 25 passed.
Final all-member omission/count-closure/Layout batch: 105 passed. CI38978173162
identified one schema-annotation omission (examples and branch descriptions),
now corrected; the annotation validator passes locally. No behavior gate is waived.
Schema equivalence after reconciliation: two explicit widening deltas, 36 equal
schemas, 576 documents/739 probes; L2+L3 20.7 seconds within its 60-second gate.
The proven-stale I1583 schema delta was pruned; frozen definitions are unchanged.
Product-head PR CI passed and shared-design YAML adoption is accepted.
After reconciliation to ready main `0b7ad6558`, current-head PR CI and the exact
review-containing main three-OS release remain required before issue closure.
