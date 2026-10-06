<!-- chrona:literal-acceptance/v1 -->

# Acceptance review: Theme token references and expressions (#1151)

PR [#1184](https://github.com/tya5/chrona/pull/1184) merged as [`9e117b73`](https://github.com/tya5/chrona/commit/9e117b73ecc90bb756a820f4e0706da1f5d82d02); its PR checks (conformance, three pytest shards, newest-Python reproduction, derived-ready) were green on the rebased head. Rule, owner decisions and scope are in the [Status comment](https://github.com/tya5/chrona/issues/1151#issuecomment-6011152909); the normative text is [Specification 07 section 5.4](../../specification/07-style-and-theme.md). The three-OS exact-main run is cited in the closing comment.

## Literal issue acceptance

### Issue #1151

- Source: [Issue #1151](https://github.com/tya5/chrona/issues/1151)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | An alias resolves to its target. | met | [Alias test](../../../tests/unit/chrona/presentation/model/test_theme_references.py) `test_an_alias_resolves_to_its_target_with_the_targets_own_number_form`; [resolver](../../../src/chrona/presentation/model/theme_references.py). | none |
| 2 | Changing a base token changes every alias. | met | [Base-change test](../../../tests/unit/chrona/presentation/model/test_theme_references.py) `test_changing_a_base_token_changes_every_alias_and_chains_follow`, and the derived-Theme override test in the same file. | none |
| 3 | An expression evaluates exactly, with the same decimal rules as today's numbers. | met | Exact `Decimal(str(number))` arithmetic, the rule `ThemeTokenView.number` applies; [expression and float-token tests](../../../tests/unit/chrona/presentation/model/test_theme_references.py) incl. `0.1 + 0.2 = 0.3`. The issue's `×` and `÷` are spelled `*` and `/`; no functions, as proposed. | none |
| 4 | A cycle or unknown reference fails at its pointer. | met | [Cycle, unknown, type, syntax and zero-divide tests](../../../tests/unit/chrona/presentation/model/test_theme_references.py) assert the typed code and `/body/values/<token>/value[/ref or /expr]`; the closure surfaces the same code and pointer. A non-number is `E_THEME_REF_TYPE` at its pointer. | none |
| 5 | A Theme with no references gives byte-identical output. | met | `resolve_references` returns the same object and the closure keeps the source-byte identity ([test](../../../tests/unit/chrona/presentation/model/test_theme_references.py)); `tools/regenerate_public_examples.py --check` passed for all 64 public slides with no `examples/**` edit; the PR's conformance and derived-preview gates passed. | none |

Proposal items outside the five rows: resolution happens once at load (draft and snapshot ingress, after inheritance); resolved values, not expressions, enter identity (identity test); the unread-binding check sees the same consumers ([test](../../../tests/unit/chrona/presentation/model/test_theme_references.py) `test_references_do_not_hide_role_consumers_from_the_unread_check`). Out of scope by decision (Status comment): numbers inside structured tokens and role bindings; adopting the feature in the target-B Theme is the reviewer's change.

## Programme-level criteria (optional)

None.

## Architecture conclusion

References are an ingress-only Theme source form resolved before contract parsing, like Theme inheritance; Layout, Scene and adapters see plain numbers. No schema accepted-value change (S0 gate passed); no lane-G file touched.
