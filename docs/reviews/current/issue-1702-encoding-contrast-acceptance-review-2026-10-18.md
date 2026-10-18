<!-- chrona:literal-acceptance/v1 -->

# Trial 6 final acceptance review

## Literal issue acceptance

### Issue #1702

- Source: [Issue #1702](https://github.com/tya5/chrona/issues/1702)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | a synthetic 8-value domain on a 6-slot scheme gives distinct paints or a legend-keyed Other. | met | [CSV import, explicit responsible mapping, mission-light six-slot scheme, local legend Layout, distinct retained paints and emitted Other key](../../../tests/integration/test_categorical_hues_not_cycled.py). Existing folding works; neither trial inputs nor packaged resources are changed. Retained in the exact-main [three-OS release run](https://github.com/tya5/chrona/actions/runs/39166500349). | — |
| 2 | find why the gate does not judge this pair; a synthetic twin raises the warning. | met | Shape visibility chooses the readable outline. [Independent fill observation](../../../tests/unit/chrona/presentation/scene/test_contrast_policy.py), [View/Style render transport](../../../tests/integration/test_encoding_contrast.py), and [pair identity, count, full IDs and CLI separation](../../../tests/unit/chrona/usecases/test_encoding_pair_warnings.py). Final [derived snapshot](https://github.com/tya5/chrona/actions/runs/39135333129) and exact-main [three-OS release run](https://github.com/tya5/chrona/actions/runs/39166500349) pass. | — |
| 3 | the message names the missing role, the View member that needs it, and what to declare (one sentence plus the pointer). | met | [Dev B row-3 review](issue-1702-rows-3-6-acceptance-review-2026-10-19.md) records the reproduced message and pointer; [deadline-mark integration test](../../../tests/integration/test_deadline_mark.py) asserts code, pointer and wording. Included in exact-main [release run](https://github.com/tya5/chrona/actions/runs/39166500349). | — |
| 4 | both read in words, with the author's pointer (same mechanism as #1683 row 1). | met | [Dev B row-4 review](issue-1702-rows-3-6-acceptance-review-2026-10-19.md) records both messages and pointers; [View-default integration tests](../../../tests/integration/test_view_defaults.py) and [schema-diagnostic unit tests](../../../tests/unit/chrona/test_schema_diagnostics.py) cover them. Included in exact-main [release run](https://github.com/tya5/chrona/actions/runs/39166500349). | — |
| 5 | a synthetic case and the PNG. | met | [Dev B row-5 review](issue-1702-rows-3-6-acceptance-review-2026-10-19.md) documents the synthetic finish-side case, its trial limitation and the [before](assets-1702-rows-3-6/row5-trial6-before.png)/[after](assets-1702-rows-3-6/row5-trial6-after.png) PNGs. The [finish-side integration test](../../../tests/integration/test_finish_delta_finish_side.py) checks the synthetic case. Included in exact-main [release run](https://github.com/tya5/chrona/actions/runs/39166500349). | — |
| 6 | the guide matches; the docs tests cover both statements. | met | [Dev B row-6 review](issue-1702-rows-3-6-acceptance-review-2026-10-19.md) records both corrected guide statements and their tests; see [update-a-plan guide](../../guides/update-a-plan.md) and [guide integration tests](../../../tests/integration/test_update_a_plan_guide.py). Included in exact-main [release run](https://github.com/tya5/chrona/actions/runs/39166500349). | — |

## Architecture and release

[Pre-code plan](https://github.com/tya5/chrona/issues/1702#issuecomment-6248687439)
and [architecture review](https://github.com/tya5/chrona/issues/1702#issuecomment-6248759612)
publish Specs08/46/60 (`92954b7a6`) before implementation. Model closes
occurrence-local colour and View/Style source/value together. Central paint
completion alone attaches passive provenance when that encoding supplies the
final mark fill. Layout geometry, strongest-channel shape visibility and
adapters are unchanged. Same-colour glyph, legend and stroke-only overrides
do not acquire encoding provenance. Scene observes completed grounds only;
the authored mark policy controls render severity. The [pre-code corpus-policy
clarification](https://github.com/tya5/chrona/commit/caf0a3b557365e9e6901b16a601c7c4e258f1a88)
preserves the existing strict shape guarantee and reports new encoded-fill
observations as warnings; an explicit caller-only policy separates them without
changing the legacy strict evaluator or adding a Theme knob. Scene-v0.7 widens in place; v0.6 is
unchanged. No new Theme policy or project-specific branch is introduced.

The [pair-warning follow-up plan and architecture review](https://github.com/tya5/chrona/issues/1702#issuecomment-6250346803)
and Spec46 `a1e13e00a` precede its implementation. The observer retains each
occurrence and measured paint pair. One shared use-case projection groups only
computable warning-severity encoded-fill misses; runtime and corpus report use
the same key. Every primitive/ground ID and subject remains available; CLI
collapse preserves distinct pair identities without truncating their IDs.
Errors, accepted exceptions, unknown grounds and ordinary findings are unchanged.

## Programme-level criteria (optional)

Baseline [PR1717](https://github.com/tya5/chrona/pull/1717) merged after
[CI39123658948](https://github.com/tya5/chrona/actions/runs/39123658948) passed.
Its final artifact12134834769 has all50 SVGs unchanged,149 passive witnesses
and148 added diagnostic IDs across seven Scenes, with no other Scene change.
The reviewer accepted this delta and requested pair aggregation.

Follow-up focused observer/render tests:89 passed; grouping/report/transport
targets:32 passed. A read-only check of the seven committed Scenes groups148
encoded warning occurrences into45 pairs (01:5/16,02:8/26,11:8/26,12:7/18,
15:6/26,19:8/26,26:3/10). All occurrence observations are retained.

The final PR [#1728](https://github.com/tya5/chrona/pull/1728) merged as
`376fe993e70597bee8b24b5d8db32646627535cc`. Its final [CI run
39135333129](https://github.com/tya5/chrona/actions/runs/39135333129) passed
derived preview, conformance, all three pytest shards, MCP floor, and newest
Python reproduction; official derived artifact `12139518376` contains all 50
SVGs byte-identical to baseline. Seven Scenes carry the intended diagnostic
aggregation change (148 encoded-fill records to 45 grouped warnings); no
unrelated Scene change was reported. The post-merge [three-OS release run
39136683440](https://github.com/tya5/chrona/actions/runs/39136683440) passed on
source `02226224db444c9b1476cfee0ff3290dd480601f` for Ubuntu, macOS, Windows,
newest Python, and MCP floor.

The dev B rows 3–6 review is published in
[issue-1702-rows-3-6-acceptance-review-2026-10-19.md](issue-1702-rows-3-6-acceptance-review-2026-10-19.md), added by merged [PR #1738](https://github.com/tya5/chrona/pull/1738). The exact-main release run
[39166500349](https://github.com/tya5/chrona/actions/runs/39166500349) passed
on `af76f393787091c0fe040113c058f3d0571eb7d7`, which contains both A's rows
1–2 and B's rows 3–6 implementations and their prior reviews. All six literal
rows above are met with the cited synthetic, diagnostic, guide and visual
evidence. This consolidated review still needs to be published and pass the
exact-main release gate before the issue can close.
