<!-- chrona:literal-acceptance/v1 -->

# Semantic field roles — acceptance review

Implementation: [PR #1573](https://github.com/tya5/chrona/pull/1573), merged as
`0b1bac57d7ac23980a68a8583cae4fb2f5f691f5`.
[Exact-head CI](https://github.com/tya5/chrona/actions/runs/38755617904) passed.
The review-containing main commit `7ca7e5553244b1e726730ad07304c08562cf93d6`
passed the three-OS release matrix, conformance, wheel, newest-Python
materializer and MCP checks in [release38814769736](https://github.com/tya5/chrona/actions/runs/38814769736).

## Literal issue acceptance

### Issue #1559

- Source: [Issue #1559](https://github.com/tya5/chrona/issues/1559)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: grouping and a column by role; an undeclared role falls back or omits with the diagnostic; entity titles resolve. | met | [Role integration tests](../../../tests/integration/test_semantic_field_roles.py), [PR CI](https://github.com/tya5/chrona/actions/runs/38755617904). The reviewer confirms unbound-role info entries are intended for the newly role-bound generic View; byte identity applies to unchanged authored inputs and all committed public SVG/Scene files ([decision](https://github.com/tya5/chrona/issues/1559#issuecomment-6202896371)). | — |
| 2 | The generic View groups by `{fieldRole: responsible}` with fallback `objectType`, and shows a `{fieldRole: phase}` column. | met | [Generic View](../../../src/chrona/resources/presets/bundles/design-default/view.yaml). | — |
| 3 | With roles declared on a scratch copy of halcyon-1, `render --preset target-b` shows the six team bands and a phase column, viewed as PNG. | met | [Published PNG inspection](https://github.com/tya5/chrona/pull/1573): only Project roles added, no View override; six named teams and 29 Phase cells, independently viewed. Three ownerless domain group objects retain an additional explicit Unassigned band; none are filtered or inferred. | — |
| 4 | All public SVG and Scene files are byte-identical. The schema equivalence result is in the PR. The Spec and gap-record rows are updated. | met | [Exact artifact comparison](https://github.com/tya5/chrona/actions/runs/38773881889) on `6bf98f9dcb9f13ee301323d07e783afcfa84713e` confirms all 100 committed public SVG/Scene files identical. Review-containing [release38814769736](https://github.com/tya5/chrona/actions/runs/38814769736) on `7ca7e5553244b1e726730ad07304c08562cf93d6` passed the full release matrix. The [PR](https://github.com/tya5/chrona/pull/1573) records schema equivalence and Spec/gap updates. | — |

## Architecture conclusion

Project owns role meaning; model normalization resolves primary policy and
source-specific Snapshot/scenario bindings. Layout, Scene and adapters do not
look up roles. Terse classifies the free map as YAML-only. No examples changed;
reviewer owns actual HALCYON adoption. The diagnostic migration decision and
release acceptance are resolved by the review-containing release above.
