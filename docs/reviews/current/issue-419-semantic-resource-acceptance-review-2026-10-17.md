# Issue 419 — semantic resource acceptance

<!-- chrona:literal-acceptance/v1 -->

**Current authority:** [work record](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md), [Specification 07](../../specification/07-style-and-theme.md), [Specification 60](../../specification/60-declared-colour-scales.md).

V1 is merged at `ff9abcbbb`. Approved PR #1668 (`1ffa261d3`) passed all checks
in [run 39051896543](https://github.com/tya5/chrona/actions/runs/39051896543).
Its official artifact has109 paths: all50 SVGs are byte-identical; all50
Scenes differ only by semantic-vocabulary provenance; no paths retired.
Exact-main release [39053236335](https://github.com/tya5/chrona/actions/runs/39053236335)
passed all three OSes on `890af301d`. This is not S1 or parent-issue acceptance.

S1 [PR1675](https://github.com/tya5/chrona/pull/1675) merged at `0ef9952a4`.
Final head `ee7354fa1` passes every gate in
[39079786599](https://github.com/tya5/chrona/actions/runs/39079786599).
Trusted generated main is `e69d4541a`; its exact three-OS release
[39080991902](https://github.com/tya5/chrona/actions/runs/39080991902) is pending.
S2a now wires optional pinned Style through Context/Draft and the normal
`RenderRequest`, with [native Store evidence](../../../tests/integration/test_style_resource_ingress.py).
S2 scoped legends and passive Scene provenance are implemented on the WIP
branch. Combined ingress/legend/Scene/C1 checks pass67 tests; actual SVG/PNG
scope output was inspected. Native serialized Style treatment also reaches
C1's effective appearance-role lookup, not only an injected metadata fixture.
S2 official artifact, reviewer and release evidence remain pending.
Do not count WIP publication as release acceptance.

### S2 installed-wheel evidence

Source `b201711c4`; wheel SHA-256
`7f45ef93469206b1af933709e004cc07c51a53ff2c34741c121963ccf04eb2da`.
Built with `pip wheel --no-deps --wheel-dir .venv-wheel/wheels .`, then installed
non-editably with `[dev,render]` into a separate worktree `.venv-wheel`.
`chrona.__file__` resolves inside that environment's `site-packages`.
The wheel interpreter passed both `test_style_resource_ingress.py` and
`test_style_scoped_legends.py` (29 tests, `--import-mode=importlib`; only the
repository test helpers were on `PYTHONPATH`), including real CLI SVG treatment.
It also passed
`tools/wheel_smoke.py` from `/tmp`, outside the checkout. This is local
packaging evidence, not the exact-main three-OS release gate.

Final-filter review exposed suppressed positive-bounds table text retaining a
potential legend. The new native regression failed before the correction;
Layout now excludes completed `overflow="suppressed"` text, matching the
published S2 rule. The scoped-legend module passes15 tests, including repeated
same-field columns, actual fill/Scene validation and suppression. No design
or public-output policy changed.
Combined ingress/legend/content/Scene regression check passed41 tests.
The native CLI test now renders both the no-Style and explicit `--style`
paths and verifies their actual SVG paint differs; the complete ingress module
passes14 tests.

The local 50-slide S2 batch introduces no SVG/Scene delta beyond the accepted
S1 glyph migration. Corrected glyph output equals S1 exactly; S1's official
final-head snapshot has109 paths, all byte-identical to the PNG-reviewed
evidence. No generated file was edited. S2's own official PR artifact remains
required against the now-generated S1 base.

## Literal issue acceptance

### Issue #419

- Source: [Issue #419 and consolidated #433](https://github.com/tya5/chrona/issues/419)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The semantic vocabulary is a versioned resource with a schema. | met | [Vocabulary resource](../../../src/chrona/resources/semantic-vocabulary.yaml), [schema](../../../schemas/semantic-vocabulary-v0.1.schema.yaml), immutable loader and typed-ingress tests. V1 official artifact and exact-main release evidence are above. | — |
| 2 | A design set can introduce a visual distinction the product did not anticipate, without a code change. | not met | S1 is merged; [native S2 Store/CLI tests](../../../tests/integration/test_style_resource_ingress.py) and wheel evidence prove authored treatment. S2 PR, reviewer and exact-main release acceptance remain required. | — |
| 3 | The presentation coverage report derives distinctions from resources rather than from source. | not met | [C1 review](issues-419-c1-acceptance-review-2026-10-18.md) covers the published vocabulary/Scene side; native S2 Style-to-Scene-to-effective-role lookup is covered. Final S2 publication and design-conformance review remain. | — |
| 4 | No field in the registry is unread. | met | The [117-entry inventory](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#v1-equivalence-inventory-117-entry-baseline), registry/Scene/contrast/reachability tests, and independent digest cover all fields. V1 official artifact shows provenance-only Scene changes. | — |
| 5 | The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes. | not met | C1 published the [purpose table](../../gallery/semantic-realization-coverage.md), checked by `--check`; final current-main release/design review remains. | — |
| 6 | Adding a purpose to the semantic registry without a classification fails the check. | not met | C1 implements and tests the [classification gate](../../../src/chrona/presentation/model/semantic_realization.py); final current-main release/design review remains. | — |
| 7 | The 31-of-40 figure, or its successor, is visible in a committed, checked document. | not met | Published [report](../../gallery/semantic-realization-coverage.md) contains the checked51-of-72 figure; final current-main release/design review remains. | — |

## Programme-level criteria (optional)

### S1 implementation evidence and gates

The local public batch has49/50 SVG/Scene pairs byte-identical.
The reviewer-approved [outer glyph colour declaration](https://github.com/tya5/chrona/issues/419#issuecomment-6242158446)
restores planned glyph ink. Compared with main, two Actual outer parts on
`glyph-gates` change from `#35D0A0` to `#5FA8FF` because they share the symbol;
all other primitives, geometry, routes and labels are unchanged. Actual Scene
contrast evaluation reports149 findings and zero errors. Baseline glyph and
Scheme remain unchanged, and no contentIdentity pin needs updating.
Focused fill/early-paint checks pass8 tests. This intentional paint migration
follows [Specification 60](../../specification/60-declared-colour-scales.md);
generated outputs were not edited. Focused native tests include
[mark composition](../../../tests/integration/test_style_mark_composition.py),
[label composition](../../../tests/integration/test_style_label_composition.py),
[fill composition](../../../tests/integration/test_style_fill_composition.py),
and [mark paint preflight](../../../tests/integration/test_style_mark_paint_preflight.py).
They are not published release evidence.

Final CI/artifact and exact-main release links are above. The official glyph
SVG equals the PNG-inspected source; all49 other SVG/Scene pairs are unchanged.

Caller repairs retain exact package closure and typed Layout content, not
production fallbacks. The shared catalogue preserves PR1676's
`E_PROFILE_ID_DUPLICATE`; all29 field-binding/source/catalogue tests pass.
Inventory, schema, paint-capability, documented-command and caller focused
checks pass. Optional TikZ compilation is not claimed and remains out of scope.

C1's [state-to-role finding](https://github.com/tya5/chrona/issues/419#issuecomment-6242783472)
and forecast classification rationale remain final-review items with dev B.
The S1-to-S2 squash integration retains byte-identical S2 product/schema code;
an accidentally repeated Style contract was removed, not made a second authority.
Schema equivalence passes on the S1 base; the standard pruner retired5 landed
S1 L1 exceptions, retaining only applicable S2 expectations. Parent419 stays
open until S1/S2 release gates, reviewer acceptance and final literal review.
