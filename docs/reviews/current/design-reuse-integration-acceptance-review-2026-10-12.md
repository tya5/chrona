# Dev A closure acceptance review

<!-- chrona:literal-acceptance/v1 -->

Published implementation: PR1422 (shared designs/font sets), PR1404 (legend),
PR1405 (preset gallery sets), and PR1472 (actual two-project evidence/font-set ingress).
Exact-main releases38478676595 and38481430846 succeeded;1269/1392/1403/1342 are closed.
1345 has an explicit owner-approved provenance disposition; this updated review's
publication/release remains required before its closure.
The later [1341/1344 release review](../../archive/reviews/issue-1341-design-reuse-acceptance-review-2026-10-13.md)
is authoritative for those closed issues; previous integration findings are in Git.
Closure-focused batch:33 tests pass (20.80 s): shared design ingress, legend
grid, public preset evidence and font sets. Preset gallery checker tests:3PASS;
`python -m tools.check_preset_gallery_sets` exits0 on the actual library.
Architecture: ingress resolves immutable Store/revision identities and pins before pure Layout composition; completed Layout defaults feed View admission. Theme role members merge one level; font sets expand before admission. Scene/adapters retain projection/serialization ownership.

## Literal issue acceptance

### Issue #1342

- Source: [issue](https://github.com/tya5/chrona/issues/1342)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | `halcyon-1` and `chrona-roadmap` each reference one copy of a design and produce identical Scenes on both paths. | met | [Two-project integration](../../../tests/integration/test_shared_design_two_projects.py) uses isolated copies of both actual Projects/Views, one authored Target-B Theme/Scheme/Layout Store, and compares complete serialized Scenes plus SVG across actual materialize/render-review ingress. No corpus source migration or reduced Project data. | Reviewer-owned checked-in adoption remains separate under board454. |
| 2 | Editing the shared Theme updates both examples' derived evidence with no Context edits. | met | Same [two-project test](../../../tests/integration/test_shared_design_two_projects.py) edits the one shared Theme's size.body12.5→13; both Scenes/SVGs change, both paths remain exactly equal, and both raw Contexts/pins are unchanged. Project-venv focused result:1PASS60.22s. | — |

### Issue #1345

- Source: [issue](https://github.com/tya5/chrona/issues/1345)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The existing Contexts can switch to the reference with byte-identical Scenes. | met | [Owner interpretation](https://github.com/tya5/chrona/issues/1345#issuecomment-6157049134): identical SVG, completed geometry, paint and diagnostics; only the true Render Context contentIdentity may change. [Actual materializer tests](../../../tests/integration/test_font_set_materialize.py) prove exactly that for basic and JP Contexts, with original authored staging and expanded metric identities. No production identity masking. | — |

### Issue #1392

- Source: [issue](https://github.com/tya5/chrona/issues/1392)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Scene test: under `spread`, the column starts are evenly spaced and the last column ends within the slot. Under `start`, output is byte-identical. | met | [Legend grid tests](../../../tests/integration/test_legend_grid.py): spread geometry and absent-versus-start SVG byte equality; packaged executive-light path. Included in current33PASS batch. | — |
| 2 | With a declared caption gap, the first column starts at caption end plus that gap. | met | [Legend grid integration](../../../tests/integration/test_legend_grid.py) measures the completed caption and column positions; declared and default gap controls pass. Spec33 owns measurement and placement. | — |
| 3 | Do not edit `examples/**`. The reviewer adopts this in Sunday Strip (slide 25). | met | [PR1404](https://github.com/tya5/chrona/pull/1404), merged3955243; its example diff is empty. [Sunday sign-off](../../research/presentation/sunday-target-2026-09-26/README.md#reproduction-1269) records actual reviewer adoption and owner approval, including the spread key panel. | — |

### Issue #1403

- Source: [issue](https://github.com/tya5/chrona/issues/1403)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | `preset list` names only existing sets. | met | [Checker tests](../../../tests/unit/tools/test_check_preset_gallery_sets.py) exercise the actual CLI/library. Only executive-light/elevated-light name controller-z-treatment-ladder; other presets omit gallerySet. Actual checker exits0. | — |
| 2 | The new check fails on a planted unknown set name. | met | [Checker tests](../../../tests/unit/tools/test_check_preset_gallery_sets.py) plant an unknown name and assert detection plus failing checker exit. All3 tests pass. | — |
| 3 | Do not edit `examples/**`. | met | [PR1405](https://github.com/tya5/chrona/pull/1405), merged7563df4; its example diff is empty. | — |

## Closure publication gate

1392/1403 and the owner-signed-off1269 were reviewed in PR1471. New1342 evidence
passed [exact-main release38481430846](https://github.com/tya5/chrona/actions/runs/38481430846)
on08c6c9dd (three OSes, MCP floor and newest-Python reproduction);1342 is closed.
1345 now has the owner-approved met row above; publication of that updated
disposition and its containing-review release remain required before closure.
PR1471 CI38477609689 succeeded; artifact11857005167 has101 unchanged
before/after paths and no additions/retirements. Review and reviewer-sign-off source
are published; [containing-review release38478676595](https://github.com/tya5/chrona/actions/runs/38478676595) succeeded. No authored examples
changed. Layout geometry and Scene/adapter ownership remain unchanged.

Font-set ingress follow-up: [pre-code correction](https://github.com/tya5/chrona/issues/1345#issuecomment-6156512752)
reuses the already-approved pure expansion without rewriting staged Context bytes.
Materializer/font-set/init focused batch:50PASS,1 corpus test deselected (42.24s).
Import direction remains11 packages/37 inward edges. Existing explicit-assets
public output must remain unchanged in the current-head CI snapshot. No acceptance
waiver or production provenance masking; the test checks the one disclosed hash.

### Issue #1269

- Source: [issue](https://github.com/tya5/chrona/issues/1269)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A committed slide (sources only), rendered with no core change and no errors. | met | [Exact-main release38413485532](https://github.com/tya5/chrona/actions/runs/38413485532) reproduces HALCYON slide25 Scene/SVG onb1974681. Reviewer adoption PRs change YAML, not the core. Previously disclosed substrate contrast warnings were explicitly accepted in reviewer PR1390. | — |
| 2 | A comparison image and a classified gap table in the Sunday research README. | met | [Reviewer PR1470](https://github.com/tya5/chrona/pull/1470), source64c85fba, included unchanged here. The mock/output comparison was visually inspected; the README classifies tuning, delivered general knobs and deliberate font/data/placement differences. | — |
| 3 | Owner visual sign-off. | met | [Explicit owner acceptance](https://github.com/tya5/chrona/issues/1269#issuecomment-6156439384), 2026-10-14. No new visual policy imposed by this review. | — |

## Programme-level criteria (optional)

None. No reviewer-owned corpus migration is claimed from unchanged artifacts.
