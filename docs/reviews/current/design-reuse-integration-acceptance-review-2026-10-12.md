# Design-reuse integration: acceptance review

<!-- chrona:literal-acceptance/v1 -->

Design-reuse code: `2ecddad0e1a02c468726164a0ef2a76b3b75277a`; integration adopts READY `d53a1df7f773a4e99b7f0445903d8598d2673c81` by ordinary merge.
This combines PRs #1408, #1415, #1414 and #1417. Closure sweep observed
2026-10-14 on READY `b1974681e0f3c00c54b3390422aee3fab338bb17`.
PR1404/1405 are also reviewed below. Final exact-main release containing this
updated review is required before closing1392/1403/1269;1342/1345 remain open.
The later [1341/1344 release review](../../archive/reviews/issue-1341-design-reuse-acceptance-review-2026-10-13.md)
supersedes this record's1341 disposition. This combined record remains current
for the still-open1342/1345 items; its historical slice findings are unchanged.
Closure-focused batch:33 tests pass (20.80 s): shared design ingress, legend
grid, public preset evidence and font sets. Preset gallery checker tests:3PASS;
`python -m tools.check_preset_gallery_sets` exits0 on the actual library.
Schema equivalence passes: one additive schema, two declared changed schemas, 35 equal schemas, 739 diagnostic probes; L2+L3 17.0 s.
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
| 1 | The existing Contexts can switch to the reference with byte-identical Scenes. | not met | [Conversion question](https://github.com/tya5/chrona/issues/1345#issuecomment-6156429891): truthful Context provenance changes Scene bytes. Additionally, materializer closure copying reads raw `fontMetrics.assets` before fontSet expansion; named-set materialization requires repair and integration evidence. Parsed-contract equality does not cover that path. | Materializer normalization repair; owner provenance decision |

## Programme-level criteria (optional)

Previous integration CI38155112260 passed with46 unchanged Scene/SVG pairs.
Integration checks/artifacts are tracked in [PR1422](https://github.com/tya5/chrona/pull/1422),
which merged at693d42f8. Exact-head CI38167971266 succeeded; artifact11712968206
contains101 paths with all46 Scene/SVG pairs unchanged and only three managed
report changes. This is implementation evidence, not converted-Context evidence.
This publishes approved foundation slices, not completed five-design adoption.
Current unresolved evidence: [1342 two-project/Theme clarification](https://github.com/tya5/chrona/issues/1342#issuecomment-6156430215)
and [1345 truthful provenance clarification](https://github.com/tya5/chrona/issues/1345#issuecomment-6156429891).
Do not close1342/1345 without their literal evidence or an explicit owner disposition.

### Issue #1392

- Source: [issue](https://github.com/tya5/chrona/issues/1392)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Scene test: under `spread`, the column starts are evenly spaced and the last column ends within the slot. Under `start`, output is byte-identical. | met | [Legend grid tests](../../../tests/integration/test_legend_grid.py): spread geometry and absent-versus-start SVG byte equality; packaged executive-light path. Included in current33PASS batch. | — |
| 2 | With a declared caption gap, the first column starts at caption end plus that gap. | met | Same integration test measures the completed caption and column positions; declared and default gap controls pass. Spec33 owns measurement and placement. | — |
| 3 | Do not edit `examples/**`. The reviewer adopts this in Sunday Strip (slide 25). | met | [PR1404](https://github.com/tya5/chrona/pull/1404), merged3955243; its example diff is empty. [Sunday sign-off](../../research/presentation/sunday-target-2026-09-26/README.md#reproduction-1269) records actual reviewer adoption and owner approval, including the spread key panel. | — |

### Issue #1403

- Source: [issue](https://github.com/tya5/chrona/issues/1403)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | `preset list` names only existing sets. | met | [Checker tests](../../../tests/unit/tools/test_check_preset_gallery_sets.py) exercise the actual CLI/library. Only executive-light/elevated-light name controller-z-treatment-ladder; other presets omit gallerySet. Actual checker exits0. | — |
| 2 | The new check fails on a planted unknown set name. | met | Same tests plant an unknown name and assert detection plus failing checker exit. All3 tests pass. | — |
| 3 | Do not edit `examples/**`. | met | [PR1405](https://github.com/tya5/chrona/pull/1405), merged7563df4; its example diff is empty. | — |

## Closure publication gate

1392/1403 and the owner-signed-off1269 are ready for release acceptance;
1342/1345 retain the not-met rows
above. No new semantics, product code or authored examples in this review update.
Ingress, Layout geometry and Scene/adapter ownership remain unchanged. Review PR,
current-head artifact comparison, and exact-main three-OS release are pending.

### Issue #1269

- Source: [issue](https://github.com/tya5/chrona/issues/1269)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A committed slide (sources only), rendered with no core change and no errors. | met | Existing HALCYON slide25 sources and committed Scene/SVG are included in the green exact-main release38413485532 onb1974681. Reviewer adoption PRs change YAML, not the core. Previously disclosed substrate contrast warnings were explicitly accepted in reviewer PR1390. | — |
| 2 | A comparison image and a classified gap table in the Sunday research README. | met | [Reviewer PR1470](https://github.com/tya5/chrona/pull/1470), source64c85fba, included unchanged here. The mock/output comparison was visually inspected; the README classifies tuning, delivered general knobs and deliberate font/data/placement differences. | — |
| 3 | Owner visual sign-off. | met | [Explicit owner acceptance](https://github.com/tya5/chrona/issues/1269#issuecomment-6156439384), 2026-10-14. No new visual policy imposed by this review. | — |
