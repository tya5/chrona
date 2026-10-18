<!-- chrona:literal-acceptance/v1 -->

# Trial 6 follow-up acceptance review

## Literal issue acceptance

### Issue #1702

- Source: [Issue #1702](https://github.com/tya5/chrona/issues/1702)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | a synthetic 8-value domain on a 6-slot scheme gives distinct paints or a legend-keyed Other. | met | [CSV import, explicit responsible mapping, mission-light six-slot scheme, local legend Layout, distinct retained paints and emitted Other key](../../../tests/integration/test_categorical_hues_not_cycled.py). Existing folding works; neither trial inputs nor packaged resources are changed. | — |
| 2 | find why the gate does not judge this pair; a synthetic twin raises the warning. | met | Existing figure visibility intentionally chooses the readable outline. [Independent encoded-fill twin and unencoded negative, multipart/opacity/policy cases](../../../tests/unit/chrona/presentation/scene/test_contrast_policy.py); [real View and Style → Scene/SVG warning/error transport](../../../tests/integration/test_encoding_contrast.py). | — |
| 3 | the message names the missing role, the View member that needs it, and what to declare (one sentence plus the pointer). | not met | [Dev B lane](https://github.com/tya5/chrona/issues/454); not accepted by the rows1–2 implementation. | — |
| 4 | both read in words, with the author's pointer (same mechanism as #1683 row 1). | not met | [Dev B lane](https://github.com/tya5/chrona/issues/454); not accepted by the rows1–2 implementation. | — |
| 5 | a synthetic case and the PNG. | not met | [Dev B lane](https://github.com/tya5/chrona/issues/454); not accepted by the rows1–2 implementation. | — |
| 6 | the guide matches; the docs tests cover both statements. | not met | [Dev B lane](https://github.com/tya5/chrona/issues/454); not accepted by the rows1–2 implementation. | — |

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

Focused component/caller batch: 1,471 passed; final targeted additions: 39 and
34 passed. Schema equivalence against ready `96bdfbb7c` passes with two exact
Scene deltas and no newly invalid documents. Independent review also found
and corrected a direct-observer admission gap; raw non-mark/Text witnesses
now fail structurally, including when no serializer is involved (81 focused
observer/policy/report tests passed).

## Programme-level criteria (optional)

Official candidate [CI39122240206](https://github.com/tya5/chrona/actions/runs/39122240206),
source `8b92a6495`, artifact12134274661: all50 SVGs are byte-identical. Seven
Scenes gain149 passive encoding witnesses and148 warning identities; after
removing only those new fields/diagnostics, every Scene is unchanged. The
contrast report keeps all existing findings: 8,514→8,663 findings, 0→0 errors,
417→565 warnings. No geometry, paint, text, route or existing diagnostic changes.
The final candidate must repeat that comparison after following #1714's ready
main. CI identified stale diagnostic/snapshot expectations and missing schema
annotations, which must pass before publication.

Release pending: focused checks and the candidate snapshot are not substitutes
for final-head checks and exact-main three-OS release. This shared issue stays
open until all six literal rows and the release gate are accepted.
