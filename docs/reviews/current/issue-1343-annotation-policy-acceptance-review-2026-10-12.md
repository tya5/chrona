<!-- chrona:literal-acceptance/v1 -->
# Reusable annotation policy acceptance (#1343)

Source implementation: `b60432b7ea1f49f946ec016ba16cb74f9d7b2864` on READY
`53ad70d98cb19fd974938b6c39d96980f2c4db09`.
[Published plan/design/architecture review](../../planning/active/issue-1343-annotation-policy-implementation-plan-2026-10-12.md).
Local evidence only; PR artifact review and containing-review three-OS release
remain required. Do not close from these local dispositions.

## Literal issue acceptance

### Issue #1343

- Source: [Issue #1343](https://github.com/tya5/chrona/issues/1343)
- Observed: 2026-10-12

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | All five designs drop their per-id `annotations` list and still place HALCYON's three notes identically. | met | [Five real designs](../../../tests/integration/test_reusable_annotation_policy.py): disposable migration removes the list; all completed primitives, diagnostics and actual SVG bytes equal the explicit form. Every public baseline SVG and primitive is also unchanged. | — |
| 2 | A project with different notes places them by kind. | met | [Different Project and synthetic migration twin](../../../tests/integration/test_reusable_annotation_policy.py), [semantic rules](../../../tests/unit/chrona/presentation/review/test_annotation_expansion.py): kind/shape, selected/folded membership, immutable order, overrides, collisions and truthful failures. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation diff](https://github.com/tya5/chrona/compare/53ad70d98cb19fd974938b6c39d96980f2c4db09...b60432b7ea1f49f946ec016ba16cb74f9d7b2864) contains no authored examples or managed evidence; permanent adoption remains reviewer-owned. | — |

## Programme-level criteria (optional)

Focused migration/semantic/status/anchor/source/heading batch:42 PASS86.43s;
closed-source unit/semantic batch:23 PASS0.69s. Five-design sweep is `corpus`
with a synthetic primitive/SVG twin in the PR path. Schema equivalence PASS:
1 additive/1 exact declared delta/36 equal,739 probes; L2+L3=17.6s.
Shared schema inventory/annotations/references, inward imports (11/37), Layout
float accumulation and literal-review validation pass.

Measurement migration disclosed: target B/Yuya/Marquee gain one annotation-host
fit warning each, with zero primitive or SVG changes; Title Card/Sunday have
no baseline change. Explicit and automatic forms retain equal diagnostics.
The numbered synthetic golden changes only12 slot/column metadata values;
all primitives, diagnostics and SVG bytes stay identical. No compatibility
measurement branch, schema waiver or corpus edit hides these changes.
Layout remains measurement/search/geometry owner; semantic expansion only
closes ordinary immutable intent. Scene/adapters are unchanged.
Full public snapshot counts and release CI are pending, not inferred from
this five-design subset.
