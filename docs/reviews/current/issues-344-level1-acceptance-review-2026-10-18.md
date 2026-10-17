<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review — #344 (Level 1 pass only)

Observed on `main` at `d11fd42b0`, which contains [PR #1667](https://github.com/tya5/chrona/pull/1667) (`ed552540`), [PR #1674](https://github.com/tya5/chrona/pull/1674) (`b4474974`), [PR #1676](https://github.com/tya5/chrona/pull/1676) (`044e7f5d`) and the derived-sync bot commit after #1676. This review covers **this pass only**: the reviewer's literal acceptance for the Level 1 typed-field pass in [issue #344 comment 6234966270](https://github.com/tya5/chrona/issues/344#issuecomment-6234966270) (three rows), plus the reviewer's two "must fail" additions (undeclared bare key; duplicate profile ID across packages, Spec 11). **Issue #344 itself stays open**: `extends` profiles and new object kinds, references, Level 2 derived expressions, Level 3 code plugins and domain packages are outside this pass and remain on it (see the programme section).

Tests were run on this base in a private venv (`PYTHONPATH=src:.`, no install into a shared environment): `pytest tests/integration/test_generic_profile_fields.py tests/integration/test_declared_field_color_encoding.py` 12 passed (8 and 4). The PNG was opened and inspected.

Delivering PRs:

| Issue | Developer PRs | Reviewer PRs |
| --- | --- | --- |
| #344 (Level 1 pass) | [#1667](https://github.com/tya5/chrona/pull/1667) (generic typed-field validation, Spec 17), [#1674](https://github.com/tya5/chrona/pull/1674) (`colorEncoding` over a declared string/enum/boolean field, Spec 60), [#1676](https://github.com/tya5/chrona/pull/1676) (`E_PROFILE_ID_DUPLICATE`) | none |

## Literal issue acceptance

### Issue #344

- Source: [Issue #344 comment 6234966270](https://github.com/tya5/chrona/issues/344#issuecomment-6234966270)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Project declares a typed field and a value on an object without Python; an unknown field, a wrong type and an out-of-enum value each fail with a pointer. | met | The fixture in [`test_generic_profile_fields.py`](../../../tests/integration/test_generic_profile_fields.py) is a pure-data profile package (`acme-risk.item` with `enum`, `number`, `boolean`, `date`, many-`string` fields) and a pure-data Project; no Python plugin is involved. `test_valid_typed_fields_pass` passes, including explicit `null` on an optional field. Failures, each with an instance pointer: `test_unknown_field_is_pointed` gives `E_PROFILE_FIELD_UNKNOWN` at `/objects/a/fields/rsk`; `test_wrong_types_are_pointed` gives `E_PROFILE_FIELD_TYPE` for a string or boolean in a number field, a non-boolean, an invalid date and a scalar in a many field; `test_out_of_enum_is_pointed` gives `E_PROFILE_FIELD_ENUM` at `/objects/a/fields/risk`. Absent differs from null: `test_required_absent_vs_null` (`E_PROFILE_FIELD_REQUIRED` at `/fields` vs `/fields/risk`). Rules in [Spec 17](../../specification/17-implementation-delivery-profile.md) (paragraph "Every other resolved profile package (#344)"). The same out-of-enum failure also fires on the render path: `test_an_undeclared_value_fails_with_a_pointer_before_colouring` in [`test_declared_field_color_encoding.py`](../../../tests/integration/test_declared_field_color_encoding.py). Limit: field types checked are the existing `profile-v0.3` scalar, array and reference shapes; reference targets are not resolved (references stay on the issue). | — |
| 2 | A View colours planned marks by that declared field through `colorEncoding` with no code change, shown on a synthetic fixture and its PNG. | met | [`test_enum_field_colours_planned_marks_and_exports_a_picture`](../../../tests/integration/test_declared_field_color_encoding.py): a synthetic Project declares `acme.risk` (enum) in a pinned profile package; the packaged default View gains only a `colorEncoding` with `source: {field: acme.risk}`; planned marks `alpha`, `beta`, `gamma` take the declared low, high and medium fills. [`test_boolean_field_colours_planned_marks`](../../../tests/integration/test_declared_field_color_encoding.py) does the same for a boolean (`true`/`false`). The same accessor is used (one shared `scale_text` rule, no second evaluator), documented in [Spec 60](../../specification/60-declared-colour-scales.md). PNG opened: [declared-enum-field-colour-encoding.png](assets-344/declared-enum-field-colour-encoding.png) shows three task bars, Alpha green, Beta red, Gamma amber, and a legend with LOW, MEDIUM and HIGH swatches in the same colours. Honest limits: admitted sources are string, enum and boolean only; a `number` source fails with `E_PRESENTATION_SCALE_VALUE` (`test_number_source_is_not_admitted_yet`) and `date` is likewise not admitted, because binning is deferred (Spec 60). The PNG is one enum fixture; the boolean case is test-only. | — |
| 3 | Existing Projects without declarations render unchanged (count table). | met | [PR #1674 body](https://github.com/tya5/chrona/pull/1674): `tools/regenerate_public_examples.py --check` PASS on 50 slides, 0 routes, 0 labels, 0 primitives changed, 0 new diagnostics; [PR #1676 body](https://github.com/tya5/chrona/pull/1676) repeats the same 0/0/0/0 for the duplicate check, and [PR #1667 body](https://github.com/tya5/chrona/pull/1667) states 0 public deltas (only Projects with a resolved non-delivery package and objects typed by its profiles are newly validated). Re-run here on `d11fd42b0` (private venv, `PYTHONPATH=src:.`, with the `chrona-fonts-noto-cjk` package installed there): `tools/regenerate_public_examples.py --check` printed `Public materializers: PASS (50 slides)`, exit 0, and left the working tree clean (no `examples/` change). | — |
| 4 | Must fail: an undeclared bare key on a profile-typed object fails with `E_PROFILE_FIELD_UNKNOWN`. | met | [`test_unknown_field_is_pointed`](../../../tests/integration/test_generic_profile_fields.py): the key `rsk` (neither declared nor namespaced) on an `acme-risk.item` object yields exactly `[("E_PROFILE_FIELD_UNKNOWN", "/objects/a/fields/rsk")]` and nothing else. Rule and code in [Spec 17](../../specification/17-implementation-delivery-profile.md); raised from `validate_profiles` in [`profiles.py`](../../../src/chrona/extensions/profiles.py) with a hint naming the profile. Objects whose `type` names no declared profile are deliberately not checked (`test_invalid_package_and_untouched_objects`), so the failure applies to profile-typed objects only, as stated. | — |
| 5 | Must fail: a profile ID declared by two packages fails with `E_PROFILE_ID_DUPLICATE` (Spec 11, globally unique profile IDs). | met | [`test_duplicate_profile_id_across_packages_names_both_packages`](../../../tests/integration/test_generic_profile_fields.py): two packages declaring `acme-risk.item` give exactly `E_PROFILE_ID_DUPLICATE` at `/extensions/1`, and the message names the profile and both packages. [`test_duplicate_of_a_delivery_profile_id_is_reported`](../../../tests/integration/test_generic_profile_fields.py): a collision with an `implementation-delivery` profile ID is also reported. The first declaration stays in effect and the later duplicate is not used. Rule: [Spec 11](../../specification/11-extension-model.md) ("globally unique profile ID") and [Spec 17](../../specification/17-implementation-delivery-profile.md). | — |

## Programme-level criteria (optional)

Issue #344's own body (re-fetched 2026-10-18 with `gh issue view 344`) has 15 acceptance checkboxes, all still unchecked. They are the whole ecosystem, not this pass. This pass advances only the parts named here; the issue stays open.

| Issue body acceptance row | State after this pass |
| --- | --- |
| Adding ordinary typed domain data does not require Python | advanced for typed scalar fields on profile-typed objects (rows 1 and 4 above); not closed, since relations and references are not covered |
| Declarative packages define profiles, typed fields and typed relations | fields only; typed relations remain open |
| Bounded deterministic derived fields (Level 2) | open, not started |
| Extension data projected through View/Style/Presentation using typed references | advanced for `colorEncoding` of string/enum/boolean fields; table columns, grouping, filter, badges, number and date sources remain open |
| Renderers never inspect arbitrary extension fields | no regression: the field is read by the existing View accessor; not separately re-audited here |
| Custom relations distinct from scheduling dependencies | open |
| Presentation Packages declare required/optional capabilities; compatibility checking; missing capability diagnostics | open |
| Domain and Presentation packages separately governed; executable plugins not required; separate executable trust boundary | open (executable boundary not started) |
| AI/GUI/CLI use the same resolved schema and Command validation | open |
| Immutable identity and provenance preserved | existing pinned package identity is used by the fixture; no new work |
| Design/specification review closes before implementation | open; the reviewer narrowed this pass to Level 1 and pulled it forward |

Remaining on #344: `extends` profiles and new object kinds, references between objects, relations, Level 2 expressions, Level 3 plugins, capability manifest and compatibility, domain packages.

Public side effects, re-measured:

| Surface | Routes | Labels | Primitives | Diagnostics |
| --- | ---: | ---: | ---: | ---: |
| #1667, #1674, #1676: public examples (0 of 50 slides) | 0 | 0 | 0 | 0 |
| This review (docs and no new image) | 0 | 0 | 0 | 0 |

## Architecture conclusion

Level 1 is a data-only path: a profile package declares typed fields, `validate_profiles` checks every resolved non-delivery package with one family of pointed `E_PROFILE_*` diagnostics (including unique profile IDs), and View projects a declared field through the same `colorEncoding` accessor as built-in fields, with one shared text rule and no profile-specific path. All five rows are met for this pass. Limits stated, not hidden: number and date colour sources are deferred (binning), references are shape-checked only, and the PNG shows the enum case. #344 must not close on this review.
