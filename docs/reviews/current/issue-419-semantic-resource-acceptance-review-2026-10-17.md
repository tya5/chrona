# Issue 419 — semantic resource acceptance

<!-- chrona:literal-acceptance/v1 -->

**Current authority:** [work record](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md), [Specification 07](../../specification/07-style-and-theme.md), [Specification 60](../../specification/60-declared-colour-scales.md).

V1 is merged at `ff9abcbbb`. Approved PR #1668 (`1ffa261d3`) passed all checks
in [run 39051896543](https://github.com/tya5/chrona/actions/runs/39051896543).
Its official artifact has109 paths: all50 SVGs are byte-identical; all50
Scenes differ only by semantic-vocabulary provenance; no paths retired.
The V1 release gate is not the S1 or parent-issue acceptance gate.

S1 is PR #1675 at `06a99ee80`, not merged or release-accepted. Typed facts, parsed-rule
evaluation, source-local identities, and role/fill composition are connected
through normalization, Layout, and Scene. Selected-mark early paint preflight
is connected; the final Style/native batch passes131 tests, with shared
catalogue/part requirements, inward imports and292 reachable modules.
S2a now wires optional pinned Style through Context/Draft and the normal
`RenderRequest`, with [native Store evidence](../../../tests/integration/test_style_resource_ingress.py).
S2 scoped legends and passive Scene provenance are implemented on the WIP
branch. Final contract/native checks passed203 tests; final ingress/consumer/
legend checks passed33. Actual SVG/PNG scope output was inspected. Official
S2 official artifact, reviewer and release evidence remain pending.
Do not count WIP publication as release acceptance.

### S2 installed-wheel evidence

Source `e7e904ee0`; wheel SHA-256
`b666525d11e466ea3e563851061b8860cf39c6933e220097db0cd74b82f7c22b`.
Built with `pip wheel --no-deps . packages/chrona-fonts-noto-cjk`, then installed
non-editably with `[dev,render]` into a separate worktree `.venv-wheel`.
`chrona.__file__` resolves inside that environment's `site-packages`.
The wheel interpreter passed both `test_style_resource_ingress.py` and
`test_style_scoped_legends.py` (26 tests, `--import-mode=importlib`; only the
repository test helpers were on `PYTHONPATH`). It also passed
`tools/wheel_smoke.py` from `/tmp`, outside the checkout. This is local
packaging evidence, not the exact-main three-OS release gate.

Final-filter review exposed suppressed positive-bounds table text retaining a
potential legend. The new native regression failed before the correction;
Layout now excludes completed `overflow="suppressed"` text, matching the
published S2 rule. The scoped-legend module passes15 tests, including repeated
same-field columns, actual fill/Scene validation and suppression. No design
or public-output policy changed.
Combined ingress/legend/content/Scene regression check passed41 tests.

The final 50-slide public batch is49 byte-identical SVG/Scene pairs and the
known `glyph-gates` pair only. Both differing files are byte-identical to the
previous S1 glyph-fill evidence: S2 introduces no additional public corpus
delta. `regenerate_public_examples.py --check --jobs 4` still fails with
`E_MATERIALIZER_MISMATCH` for that declared paint migration; an aggregating
read-only materializer batch confirms all50 outcomes. No generated file was
edited. This does not waive the unresolved S1 contrast gate.

## Literal issue acceptance

### Issue #419

- Source: [Issue #419 and consolidated #433](https://github.com/tya5/chrona/issues/419)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The semantic vocabulary is a versioned resource with a schema. | met | [Vocabulary resource](../../../src/chrona/resources/semantic-vocabulary.yaml), [schema](../../../schemas/semantic-vocabulary-v0.1.schema.yaml), immutable loader and typed-ingress tests. Official V1 PR evidence is above; exact-main release [39053236335](https://github.com/tya5/chrona/actions/runs/39053236335) passed. | — |
| 2 | A design set can introduce a visual distinction the product did not anticipate, without a code change. | not met | S1 implements Style evaluation and composition on its WIP branch; [S2 resource ingress](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#architecture-review-and-proposed-implementation-sequence) and published end-to-end evidence remain required. | — |
| 3 | The presentation coverage report derives distinctions from resources rather than from source. | not met | [C1](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#architecture-review-and-proposed-implementation-sequence) remains dev B's scope; the current report is not resource-derived. | — |
| 4 | No field in the registry is unread. | met | The [117-entry inventory](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#v1-equivalence-inventory-117-entry-baseline), registry/Scene/contrast/reachability tests, and independent digest cover all fields. V1 official artifact shows provenance-only Scene changes. | — |
| 5 | The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes. | not met | C1 must derive and publish the corpus population in the [coverage report](../../gallery/semantic-realization-coverage.md). | — |
| 6 | Adding a purpose to the semantic registry without a classification fails the check. | not met | C1 must connect the complete purpose population to the [classification gate](../../../src/chrona/presentation/model/semantic_realization.py); current code does not yet enforce this. | — |
| 7 | The 31-of-40 figure, or its successor, is visible in a committed, checked document. | not met | C1 must publish the current derived fraction in the [checked report](../../gallery/semantic-realization-coverage.md); the historical figure is not current evidence. | — |

## Programme-level criteria (optional)

### S1 implementation evidence and gates

The current local public batch has49/50 SVG/Scene pairs byte-identical.
`glyph-gates` changes eight inherited glyph fills, with no geometry, route or
label changes, and adds one mark-contrast warning. Root inspected its PNG.
This intentional paint migration follows [Specification 60](../../specification/60-declared-colour-scales.md);
no examples or generated outputs were edited. Focused native tests include
[mark composition](../../../tests/integration/test_style_mark_composition.py),
[label composition](../../../tests/integration/test_style_label_composition.py),
[fill composition](../../../tests/integration/test_style_fill_composition.py),
and [mark paint preflight](../../../tests/integration/test_style_mark_paint_preflight.py).
They are not published release evidence.

Exact-main release run
[39053236335](https://github.com/tya5/chrona/actions/runs/39053236335) passed on
890af301d, including all three OSes, reproduction and MCP. S1 PR CI
[39058512156](https://github.com/tya5/chrona/actions/runs/39058512156) fails at
the opted-in glyph-gates contrast gate; reproduction/readiness failures follow
the missing generated snapshot. Reviewer-owned explicit glyph colour approval
is requested on419; do not weaken the threshold. Before accepting S1,
inspect official batched SVG/Scene and PNG
evidence, and verify the exact-main three-OS release. Keep #419 open until S1,
S2 and C1 satisfy their respective acceptance rows.
