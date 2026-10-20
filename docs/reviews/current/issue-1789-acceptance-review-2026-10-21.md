<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1789 rows 1 to 3

Observed on `main` at `e9aeef54e`. [Issue #1789](https://github.com/tya5/chrona/issues/1789) has three acceptance rows. They landed through [PR #1795](https://github.com/tya5/chrona/pull/1795) (merge `3892fff26`: code, Spec 60, schemas, guide, example, tests). The issue body and comments were re-fetched with `gh issue view 1789 -R tya5/chrona --json body,comments` on 2026-10-21 and counted literally: three numbered rows, no comments, none added since the first reading. The Rule section (absent or null keeps base paint, out-of-domain stays refused, optional `missing:`) is covered through rows 1 and 2.

## Method

Private venv, `PYTHONPATH=<worktree>/src:<worktree>`, no shared install. The trial-9 inputs were read from the evidence branch commit `1ea198371` (`trial-9/typed/*`) in a read-only worktree and not committed. The command is the guide's `chrona render risk.chrona --preset <p> --view typed-risk-view.yaml`, run in `trial-9/typed`. `executive-light` and `target-b` also take the guide's section 3a Theme and Color Scheme (`typed-executive-theme.yaml` and `typed-executive-scheme.yaml`, `typed-target-b-theme.yaml` and `typed-target-b-scheme.yaml`), because those presets declare no `series` scale. Without them the render stops at `E_PRESENTATION_SCALE_MAPPING ... slots=None`, the refusal the guide's 3a documents and which is a different rule from this issue's. The Style case is `--preset wallboard-dark --style all-risk-style.yaml`. Each render was run to SVG with `--emit-scene` (to read the fill of the `kickoff` object) and to PNG. Tests run: `tests/integration/test_encoding_missing_value.py` (7 passed) and `tests/unit/chrona/skills/test_chrona_skill.py` with `tests/unit/tools/test_wheel_doc_check.py` (25 passed). The full suite was not run.

## Literal issue acceptance

### Issue #1789

- Source: [Issue #1789](https://github.com/tya5/chrona/issues/1789)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The trial-9 command renders on all four presets and with the Style rule; the gate shows base paint. | met | All five renders exit 0 with status `ok` and no diagnostics (the issue observed `E_PRESENTATION_SCALE_VALUE object='kickoff' value=None` on three presets and the Style rule): [wallboard-dark](assets-1789/risk-wallboard-dark.png) ([svg](assets-1789/risk-wallboard-dark.svg), [json](assets-1789/risk-wallboard-dark.json)), [mission-light](assets-1789/risk-mission-light.png), [executive-light](assets-1789/risk-executive-light.png), [target-b](assets-1789/risk-target-b.png), [wallboard-dark with the Style rule](assets-1789/risk-wallboard-dark-style.png). The gate shows base paint, read from the Scene fill of the `kickoff` object and not from the status ([kickoff-fills.txt](assets-1789/kickoff-fills.txt)): `#2F81F7` on wallboard-dark and with the Style rule (the preset's plain bar colour; the three risk-coloured tasks are `#2A9D43`, `#D2691E`, `#8957E5`), `#1D5FD1` on mission-light, `#3986E6` on executive-light, and `#101828` on target-b (its gate diamond, drawn as two parts with no risk colour). None of them is a risk colour of that preset, while `ledger` (risk high) is encoded on every one (for example `#B91C1C` on executive-light and target-b). `golive`, the second gate, behaves the same. | — |
| 2 | A synthetic test covers absent, null, out-of-domain and `missing: <value>`. | met | [`test_encoding_missing_value.py`](../../../tests/integration/test_encoding_missing_value.py) (7 passed here): absent, [`test_absent_value_keeps_base_paint_for_typed_and_untyped_objects`](../../../tests/integration/test_encoding_missing_value.py); null, `test_null_value_keeps_base_paint`; out-of-domain, `test_value_outside_the_domain_is_still_refused` (`E_PRESENTATION_SCALE_VALUE`); `missing: <value>`, `test_missing_names_a_domain_value_for_absent_and_null`, plus `test_missing_base_is_the_default_spelled_out`, `test_missing_outside_the_domain_is_refused` and `test_style_encode_follows_the_same_rule` (Style `encode` with and without `missing`). Rule text: Spec [60](../../specification/60-declared-colour-scales.md). | — |
| 3 | The typed-fields guide example includes a gate. | met | [`typed-fields.md`](../../guides/typed-fields.md) adds the `kickoff` gate to both the terse plan (`kickoff "Kickoff" gate 2026-11-02`) and the YAML plan, and states the rule under it; the skill example [`plan.yaml`](../../../skills/chrona/examples/typed-fields/plan.yaml) carries the same gate and the skill page [`typed-fields.md`](../../../skills/chrona/references/typed-fields.md) shows it verbatim. The page's fences equal the example files and the example runs: [`test_chrona_skill.py`](../../../tests/unit/chrona/skills/test_chrona_skill.py) `test_typed_fields_fences_equal_their_example_files_and_the_example_runs` (25 passed with the wheel doc check). The renders of row 1 use the trial plan, whose `kickoff` gate is the one in the guide. | — |

## Programme-level criteria (optional)

### Public side effects

This review adds documents and pictures only.

| Item | Routes | Labels | Primitives | New diagnostics |
| --- | ---: | ---: | ---: | ---: |
| This review (one document, five PNG and SVG pairs, five JSON results, one text summary) | 0 | 0 | 0 | 0 |

The public effect of the reviewed PR #1795 is in its own body: objects with no value for the encoded field keep base paint instead of failing or going uncoloured, and `missing:` is a new optional member of `colorEncoding` and Style `encode`.
