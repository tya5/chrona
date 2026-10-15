<!-- chrona:literal-acceptance/v1 -->

# Semantic field roles — acceptance review

Implementation: [PR #1573](https://github.com/tya5/chrona/pull/1573), merged as
`0b1bac57d7ac23980a68a8583cae4fb2f5f691f5`.
[Exact-head CI](https://github.com/tya5/chrona/actions/runs/38755617904) passed.
Release acceptance remains pending the exact-main matrix and migration decision below.

## Literal issue acceptance

### Issue #1559

- Source: [Issue #1559](https://github.com/tya5/chrona/issues/1559)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: grouping and a column by role; an undeclared role falls back or omits with the diagnostic; entity titles resolve. | met | [Role integration tests](../../../tests/integration/test_semantic_field_roles.py), [passing CI](https://github.com/tya5/chrona/actions/runs/38755617904). | — |
| 2 | The generic View groups by `{fieldRole: responsible}` with fallback `objectType`, and shows a `{fieldRole: phase}` column. | met | [Generic View](../../../src/chrona/resources/presets/bundles/design-default/view.yaml). | — |
| 3 | With roles declared on a scratch copy of halcyon-1, `render --preset target-b` shows the six team bands and a phase column, viewed as PNG. | met | [Published PNG inspection](https://github.com/tya5/chrona/pull/1573): only Project roles added, no View override; six named teams and 29 Phase cells, independently viewed. Three ownerless domain group objects retain an additional explicit Unassigned band; none are filtered or inferred. | — |
| 4 | All public SVG and Scene files are byte-identical. The schema equivalence result is in the PR. The Spec and gap-record rows are updated. | met | [Exact-head artifact11983426916](https://github.com/tya5/chrona/actions/runs/38755617904/artifacts/11983426916):50SVG+50Scene bytes identical,0added/retired. [PR](https://github.com/tya5/chrona/pull/1573) records full equivalence PASS, L1delta2/equal36 and L2+L3 19.7s/60s, Specs05/06/38/60/64 and six gap updates. | — |

## Programme-level criteria (optional)

The changed generic View necessarily adds required unbound-role info diagnostics
on Projects without roles; visible SVG is unchanged, not the old View's Scene
diagnostics. [Reviewer disposition](https://github.com/tya5/chrona/issues/1559#issuecomment-6194167626)
is unresolved. Do not silently waive the issue's default-output decision.
The implementation-containing main commit
`4ab652a5f0d0641175663f57eba9c1da499712e6` passed
[release38767049424](https://github.com/tya5/chrona/actions/runs/38767049424).
That commit does not contain this review. Release acceptance requires a
successful exact-main gate containing this review, plus resolution of the
unresolved migration disposition.

## Architecture conclusion

Project owns role meaning; model normalization resolves primary policy and
source-specific Snapshot/scenario bindings. Layout, Scene and adapters do not
look up roles. Terse classifies the free map as YAML-only. No examples changed;
reviewer owns actual HALCYON adoption. Keep the issue open until the unresolved
decision and required release evidence are complete.
