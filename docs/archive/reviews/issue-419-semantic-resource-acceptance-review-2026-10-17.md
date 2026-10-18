# Issue 419 — semantic resource acceptance

<!-- chrona:literal-acceptance/v1 -->

**Archived authority:** [work record](../planning/issue-419-semantic-resource-work-record-2026-10-17.md), [Specification 07](../../specification/07-style-and-theme.md), [Specification 60](../../specification/60-declared-colour-scales.md), and the [C1 acceptance review](issues-419-c1-acceptance-review-2026-10-18.md). The final release/closure state is recorded below.

## Published implementation and release evidence

- **V1:** vocabulary/schema implementation merged as `ff9abcbbb`; PR artifact [39051896543](https://github.com/tya5/chrona/actions/runs/39051896543) and exact-main three-OS release [39053236335](https://github.com/tya5/chrona/actions/runs/39053236335) passed. The official artifact had 109 paths: 50 SVGs unchanged, 50 Scenes changed only for vocabulary provenance, and no retired paths.
- **S1:** [PR #1675](https://github.com/tya5/chrona/pull/1675) merged at `0ef9952a4`; exact-main release [39080991902](https://github.com/tya5/chrona/actions/runs/39080991902) passed all three OSes on `e69d4541a`. The reviewed artifact contains the approved glyph colour change; no canonical generated file was hand-edited.
- **S2:** [PR #1687](https://github.com/tya5/chrona/pull/1687) merged at `5bfa5356b`; final artifact had 50 SVG/Scene pairs unchanged from its S1 base. Exact-main release [39084253511](https://github.com/tya5/chrona/actions/runs/39084253511) passed all three OSes, conformance, wheel gates and newest-Python reproduction on generated main `d9a10d4ea`.
- **Installed wheel:** source `b201711c4`, wheel SHA-256 `7f45ef93469206b1af933709e004cc07c51a53ff2c34741c121963ccf04eb2da`. A separate non-editable environment confirmed the import came from `site-packages`; native ingress/scoped-legend tests passed 29 cases, including CLI SVG treatment, and `tools/wheel_smoke.py` passed from `/tmp`. This is supplementary packaging evidence, not a replacement for the exact-main release.
- **C1 report:** PR #1678 and the wording/rationale correction [PR #1690](https://github.com/tya5/chrona/pull/1690) are merged. Current derived main is `5c7627e90`; #1690 checks passed in [39088246770](https://github.com/tya5/chrona/actions/runs/39088246770). The committed report separates observed purpose/role evidence from admitted-model cardinality; it does not claim admitted states were drawn or provide a state-to-role witness matrix.
- **Current artifact confirmation:** PR1692 source `a7fc836ac`, base `0c8179740`, [snapshot39090738185](https://github.com/tya5/chrona/actions/runs/39090738185) contains the identical checked C1 report (SHA-256 `88b4012eb86f829d26c95578d4b3ff4522229a62025e632e9f571c54207b6456`): 51/72 single-role drawn purposes, 83 registered, 11 unpainted. Its separate legend-checker conformance failure is not release acceptance; the final exact-main gate remains required.

The final review-containing main `5fe41db8e8512e5438e9ecbe67f5c56c1d18d152`
passed [exact-main release39108421823](https://github.com/tya5/chrona/actions/runs/39108421823):
all three native OS pytest/conformance/wheel gates, MCP floor and newest-Python
public-materializer reproduction. The official release succeeded; issue #419
was closed after all seven literal acceptance rows were confirmed met. Final
artifact/report evidence is recorded in the linked work record and the closure
comment on [issue #419](https://github.com/tya5/chrona/issues/419).

## Literal issue acceptance

### Issue #419

- Source: [Issue #419 and consolidated #433](https://github.com/tya5/chrona/issues/419)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The semantic vocabulary is a versioned resource with a schema. | met | [Vocabulary resource](../../../src/chrona/resources/semantic-vocabulary.yaml), [schema](../../../schemas/semantic-vocabulary-v0.1.schema.yaml), immutable loader/typed-ingress tests, and the V1 artifact/release above. | — |
| 2 | A design set can introduce a visual distinction the product did not anticipate, without a code change. | met | S1/S2 support pinned authored Style resources through the normal rendering path. [Native ingress tests](../../../tests/integration/test_style_resource_ingress.py) verify authored treatment in SVG; the installed wheel ran ingress and scoped-legend tests against site-packages, with the smoke result above. S1/S2 exact-main releases passed. | — |
| 3 | The presentation coverage report derives distinctions from resources rather than from source. | met | [`purpose_rows`](../../../tools/semantic_realization_coverage.py) derives purposes/registered roles from the vocabulary resource and observed appearance roles from committed Scene `themeRole` (else `visualRole`), including authored S1/S2 distinctions. Consolidated #433 proposal2 explicitly retains `RealizationFamily` as classification of derived rows, not their population; Python classification is therefore not a missing resource requirement. [Scope audit6245683653](https://github.com/tya5/chrona/issues/419#issuecomment-6245683653) corrects the previous interpretation. The [checked report](../../gallery/semantic-realization-coverage.md) separates admitted cardinality from observed evidence, as [decision6243966086](https://github.com/tya5/chrona/issues/419#issuecomment-6243966086) requires. Coverage tests16 and report `--check` pass. | — |
| 4 | No field in the registry is unread. | met | The [117-entry equivalence inventory](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#v1-equivalence-inventory-117-entry-baseline), registry/Scene/contrast/reachability tests, and independent digest cover the fields; the official V1 artifact records provenance-only Scene changes. | — |
| 5 | The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes. | met | The [checked purpose report](../../gallery/semantic-realization-coverage.md) has one row for each of 72 drawn purposes, with realized roles and counts; 11 registered-but-unpainted purposes are listed separately, outside the denominator. [C1 review](issues-419-c1-acceptance-review-2026-10-18.md) records the source and test evidence. | — |
| 6 | Adding a purpose to the semantic registry without a classification fails the check. | met | The [classification gate](../../../src/chrona/presentation/model/semantic_realization.py) and [coverage tests](../../../tests/unit/tools/test_semantic_realization_coverage.py) reject unclassified, unknown, and count-inconsistent classifications; #1690 checks passed, including the updated test suite. | — |
| 7 | The 31-of-40 figure, or its successor, is visible in a committed, checked document. | met | The checked [coverage report](../../gallery/semantic-realization-coverage.md) states **51 of 72** drawn purposes resolve to one realized appearance role; 21 resolve to more than one. It separately reports 83 registered purposes and 11 unpainted purposes, not counted in the denominator. | — |

## Programme-level criteria (optional)
