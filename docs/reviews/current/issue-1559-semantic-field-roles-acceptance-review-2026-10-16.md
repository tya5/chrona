<!-- chrona:literal-acceptance/v1 -->

# Semantic field roles — acceptance review

Implementation: [PR #1573](https://github.com/tya5/chrona/pull/1573), merged as
`0b1bac57d7ac23980a68a8583cae4fb2f5f691f5`.
[Exact-head CI](https://github.com/tya5/chrona/actions/runs/38755617904) passed.
Release acceptance remains pending this review's own exact-main matrix.

## Literal issue acceptance

### Issue #1559

- Source: [Issue #1559](https://github.com/tya5/chrona/issues/1559)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: grouping and a column by role; an undeclared role falls back or omits with the diagnostic; entity titles resolve. | met | [Role integration tests](../../../tests/integration/test_semantic_field_roles.py), [PR CI](https://github.com/tya5/chrona/actions/runs/38755617904). The reviewer confirms unbound-role info entries are intended for the newly role-bound generic View; byte identity applies to unchanged authored inputs and all committed public SVG/Scene files ([decision](https://github.com/tya5/chrona/issues/1559#issuecomment-6202896371)). | — |
| 2 | The generic View groups by `{fieldRole: responsible}` with fallback `objectType`, and shows a `{fieldRole: phase}` column. | met | [Generic View](../../../src/chrona/resources/presets/bundles/design-default/view.yaml). | — |
| 3 | With roles declared on a scratch copy of halcyon-1, `render --preset target-b` shows the six team bands and a phase column, viewed as PNG. | met | [Published PNG inspection](https://github.com/tya5/chrona/pull/1573): only Project roles added, no View override; six named teams and 29 Phase cells, independently viewed. Three ownerless domain group objects retain an additional explicit Unassigned band; none are filtered or inferred. | — |
| 4 | All public SVG and Scene files are byte-identical. The schema equivalence result is in the PR. The Spec and gap-record rows are updated. | met | [Review-containing release](https://github.com/tya5/chrona/actions/runs/38773881889) on `6bf98f9dcb9f13ee301323d07e783afcfa84713e` confirms all100 committed public SVG/Scene files identical. [PR](https://github.com/tya5/chrona/pull/1573) records full equivalence PASS, L1delta2/equal36 and L2+L3 19.7s/60s, Specs05/06/38/60/64 and six gap updates. | — |

## Programme-level criteria (optional)

The new `I_VIEW_FIELD_ROLE_UNBOUND` entries on role-less Projects are intended
output of the newly role-bound generic View. Byte identity applies to unchanged
authored inputs and every committed public SVG/Scene file, as confirmed by the
[reviewer disposition](https://github.com/tya5/chrona/issues/1559#issuecomment-6202896371)
and review-containing [release38773881889](https://github.com/tya5/chrona/actions/runs/38773881889).
The migration decision is resolved; this review's own exact-main release gate
is still required.

## Architecture conclusion

Project owns role meaning; model normalization resolves primary policy and
source-specific Snapshot/scenario bindings. Layout, Scene and adapters do not
look up roles. Terse classifies the free map as YAML-only. No examples changed;
reviewer owns actual HALCYON adoption. The diagnostic migration decision is
resolved; release acceptance awaits this review's exact-main gate.
