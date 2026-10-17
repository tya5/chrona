# Issue 419 — semantic resource acceptance

<!-- chrona:literal-acceptance/v1 -->

**Current authority:** [work record](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md), [Specification 07](../../specification/07-style-and-theme.md), [Specification 60](../../specification/60-declared-colour-scales.md).

V1 is merged at `ff9abcbbb`. Approved PR #1668 (`1ffa261d3`) passed all checks
in [run 39051896543](https://github.com/tya5/chrona/actions/runs/39051896543).
Its official artifact has109 paths: all50 SVGs are byte-identical; all50
Scenes differ only by semantic-vocabulary provenance; no paths retired.
Exact-main release [39053236335](https://github.com/tya5/chrona/actions/runs/39053236335)
passed all three OSes on `890af301d`. This is not S1 or parent-issue acceptance.

S1 is PR1675, not merged or release-accepted. Typed facts, parsed-rule
evaluation, source-local identities, and role/fill composition are connected
through normalization, Layout, and Scene. Selected-mark early paint preflight
is connected; the final Style/native batch passes131 tests, with shared
catalogue/part requirements, inward imports and292 reachable modules.
Style resource-reference ingress is intentionally S2 and
is not yet wired to `RenderRequest`; injected parsed-rule composition tests do
not establish that ingress. Do not count WIP publication as release acceptance.

## Literal issue acceptance

### Issue #419

- Source: [Issue #419 and consolidated #433](https://github.com/tya5/chrona/issues/419)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | The semantic vocabulary is a versioned resource with a schema. | met | [Vocabulary resource](../../../src/chrona/resources/semantic-vocabulary.yaml), [schema](../../../schemas/semantic-vocabulary-v0.1.schema.yaml), immutable loader and typed-ingress tests. V1 official artifact and exact-main release evidence are above. | — |
| 2 | A design set can introduce a visual distinction the product did not anticipate, without a code change. | not met | S1 implements Style evaluation and composition on its WIP branch; [S2 resource ingress](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#architecture-review-and-proposed-implementation-sequence) and published end-to-end evidence remain required. | — |
| 3 | The presentation coverage report derives distinctions from resources rather than from source. | not met | [C1](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#architecture-review-and-proposed-implementation-sequence) remains dev B's scope; the current report is not resource-derived. | — |
| 4 | No field in the registry is unread. | met | The [117-entry inventory](../../planning/active/issue-419-semantic-resource-work-record-2026-10-17.md#v1-equivalence-inventory-117-entry-baseline), registry/Scene/contrast/reachability tests, and independent digest cover all fields. V1 official artifact shows provenance-only Scene changes. | — |
| 5 | The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes. | not met | C1 must derive and publish the corpus population in the [coverage report](../../gallery/semantic-realization-coverage.md). | — |
| 6 | Adding a purpose to the semantic registry without a classification fails the check. | not met | C1 must connect the complete purpose population to the [classification gate](../../../src/chrona/presentation/model/semantic_realization.py); current code does not yet enforce this. | — |
| 7 | The 31-of-40 figure, or its successor, is visible in a committed, checked document. | not met | C1 must publish the current derived fraction in the [checked report](../../gallery/semantic-realization-coverage.md); the historical figure is not current evidence. | — |

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

CI [39077516079](https://github.com/tya5/chrona/actions/runs/39077516079),
head `474f3f92d`, passes snapshot/contrast, public reproduction, MCP and
conformance; pytest shards are pending. Its official snapshot has109 paths,
all byte-identical to the preceding reviewed snapshot:49 unchanged SVG/Scene
pairs, the disclosed glyph-gates pair, three diagnostic reports, no retired
paths. The official glyph SVG equals the PNG-inspected source.

Caller repairs retain exact package closure and typed Layout content, not
production fallbacks. The shared catalogue preserves PR1676's
`E_PROFILE_ID_DUPLICATE`; all29 field-binding/source/catalogue tests pass.
Inventory, schema, paint-capability, documented-command and caller focused
checks pass. Optional TikZ compilation is not claimed and remains out of scope.

C1 merged in PR1678 at `348fa338c`; its trusted generated tip must be normally
integrated and the final S1 head retested before merging. C1's state-to-role
evidence finding remains a separate final review item with dev B. S1 is not
release-accepted until current-head CI, official artifact review and exact-main
three-OS release succeed. Parent419 stays open for S2 and C1 as well.
