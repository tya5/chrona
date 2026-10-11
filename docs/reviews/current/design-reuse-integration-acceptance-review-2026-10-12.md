# Design-reuse integration: acceptance review

<!-- chrona:literal-acceptance/v1 -->

Code: `2ecddad0e1a02c468726164a0ef2a76b3b75277a`, based on READY `fa862e40745aa134198dfe070aa347c451dd7ffe`.
This combines PRs #1408, #1415, #1414 and #1417; it is not release acceptance.
69 focused tests pass (39.26 s), including shared Layout inheritance, thin View defaults and font-set expansion together with unchanged SVG bytes.
Schema equivalence passes: one additive schema, two declared changed schemas, 35 equal schemas, 739 diagnostic probes; L2+L3 17.7 s.
Import direction: 11 packages, 37 inward edges. Reachability: 232 modules, no staged/orphan modules. Authored `examples/**` diff is empty.
Merge resolutions preserve each approved declaration; conflicts were confined to Spec13 and the expected-delta ledger. No product-code resolution was needed.
Architecture: ingress resolves immutable Store/revision identities and pins before pure Layout composition; completed Layout defaults feed View admission. Theme role members merge one level; font sets expand before admission. Scene/adapters retain projection/serialization ownership.

## Literal issue acceptance

### Issue #1401

- Source: [issue](https://github.com/tya5/chrona/issues/1401)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A test: a derived Theme adds one token and one role to a base that has neither, and the resolved Theme equals a hand-merged non-derived Theme. | met | [Theme tests](../../../tests/unit/chrona/presentation/model/test_theme_inheritance.py), included in the 69-test batch. | — |
| 2 | Existing derived Themes (e.g. halcyon `12-glyph-gates`) are byte-identical. | met | [PR-head artifact audit](https://github.com/tya5/chrona/pull/1408#issuecomment-6110720540): 46 Scene/SVG pairs unchanged; integrated artifact still required. | — |
| 3 | Do not edit `examples/**`. The reviewer then rebuilds the moved feature Themes as thin variants. | met | [reviewed PR](https://github.com/tya5/chrona/pull/1408); integrated authored example diff is empty. Reviewer adoption is separate. | — |

### Issue #1341

- Source: [issue](https://github.com/tya5/chrona/issues/1341)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Target B and the four other approved designs reproduce byte-identically on HALCYON, with Theme/Layout/profiles containing no HALCYON id or wording, and with Views containing connection members only. | not met | [slice-1 evidence](https://github.com/tya5/chrona/pull/1414#issuecomment-6110796147); remaining design-member slices and reviewer restructuring are not implemented by this integration. | Remaining #1341 slices; #1343 |
| 2 | `examples/chrona-roadmap` renders each design by writing only its own thin View and Context. | not met | [current slice scope](https://github.com/tya5/chrona/issues/1341#issuecomment-6110687555); actual five-design adoption remains pending. | Reviewer restructuring after remaining slices |

### Issue #1342

- Source: [issue](https://github.com/tya5/chrona/issues/1342)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | `halcyon-1` and `chrona-roadmap` each reference one copy of a design and produce identical Scenes on both paths. | not met | [shared-design tests](../../../tests/integration/test_shared_design.py) prove the mechanism and combined ingress, not actual two-project adoption. | Reviewer restructuring |
| 2 | Editing the shared Theme updates both examples' derived evidence with no Context edits. | not met | [current scope](https://github.com/tya5/chrona/issues/1342#issuecomment-6110729990): shared-Scheme edit/Context immutability is tested, but this is not actual two-project Theme evidence. | Reviewer restructuring |

### Issue #1345

- Source: [issue](https://github.com/tya5/chrona/issues/1345)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The existing Contexts can switch to the reference with byte-identical Scenes. | not met | [actual conversion evidence/question](https://github.com/tya5/chrona/issues/1345#issuecomment-6110612395): SVG/drawing content identical, but truthful changed Context provenance changes Scene bytes. No identity falsification. | Owner decision pending |

## Programme-level criteria (optional)

Pending: integrated current-head CI/public artifacts; exact-main three-OS release on the commit containing this review. Keep #1341/#1342 actual adoption and #1345 provenance interpretation explicit; synthetic or old-base evidence does not close them.
