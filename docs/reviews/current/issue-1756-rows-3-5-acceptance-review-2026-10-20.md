<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1756 rows 3 to 5

Observed on `main` at `8dba61ab4`. [Issue #1756](https://github.com/tya5/chrona/issues/1756) has five rows. The issue body and all its comments were re-fetched with `gh issue view 1756 --json body,comments` on 2026-10-20 and counted literally: five rows, none added since the first reading. Rows 1 and 2 are dev A's (lane split on the issue, board #454) and are **out of this review**: it assesses rows 3 to 5 only. Dev A's rows are covered by [the shared customisation review](issue-1756-colour-customisation-acceptance-review-2026-10-20.md). Rows 3 to 5 landed as [PR #1765](https://github.com/tya5/chrona/pull/1765) (merge `12224ed89`, row 3) and [PR #1762](https://github.com/tya5/chrona/pull/1762) (rows 4 and 5, via issues #1760 and #1759).

## Method

Private venv, `PYTHONPATH=<worktree>/src:<worktree>`, a worktree at `origin/main`. The guide's example files [`skills/chrona/examples/typed-fields/`](../../../skills/chrona/examples/typed-fields/plan.yaml) were copied to a temp directory and the guide's own commands run with `python -m chrona`. Focused tests only, 21 passed: `tests/unit/chrona/skills/test_chrona_skill.py` and the two row 4 and row 5 tests; dev A's `test_legend_colour_warning_render.py` and `test_gate_encoding_modes.py` also pass here (5 passed) but are not assessed. The full suite was not run.

## Literal issue acceptance

### Issue #1756

- Source: [Issue #1756](https://github.com/tya5/chrona/issues/1756)
- Observed: 2026-10-20

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | an encoding whose realized slot colours are indistinct from each other, or from another legend key's colour, gets a warning naming both, using Spec 60's existing distinctness measure. Show it on a synthetic case. | not met | Dev A's row, out of this review: not assessed here, so it is not counted as met by this document. Dev A's implementation and review are in [the shared customisation review](issue-1756-colour-customisation-acceptance-review-2026-10-20.md); its release gate was still open on the issue at the time of writing. | — |
| 2 | find whether this is intended; make both modes consistent or state the rule, and add a synthetic test. | not met | Dev A's row, out of this review: not assessed here, so it is not counted as met by this document. See [the shared customisation review](issue-1756-colour-customisation-acceptance-review-2026-10-20.md) for dev A's evidence. | — |
| 3 | the guide shows the colour-by-field recipe working on at least two bundled presets, plus title and subtitle customisation, checked by the docs tests. | met | [`typed-fields.md`](../../guides/typed-fields.md) section 3a "Colour by field on a preset with no `series` scale" shows the recipe (Scheme categories `risk-low`, `risk-medium`, `risk-high`, plus a derived Theme that `extends` the preset and sets `colorScales.series.slots`) on `executive-light` and `target-b`, and says `marquee` follows the same two steps; the "Title and subtitle" subsection shows `heading.title` and `heading.subtitle`. Run here: the bare `executive-light` render is `rejected` with `E_PRESENTATION_SCALE_MAPPING` (`slots=None`, as the issue observed); with the guide's theme and scheme both presets render `status: ok`, the SVG holds `#2E7D5B`, `#B7791F` and `#B91C1C` (two uses each), the legend texts `low`, `medium`, `high`, the title "Typed fields demo: delivery risk" and the subtitle "Bars coloured by risk". Pictures: [executive-light](assets-1756/recipe-executive-light.png), [target-b](assets-1756/recipe-target-b.png). The derived Themes extend the copied presets by relative `path` with no hash pin (Spec 42). Docs test: [`test_typed_fields_colour_recipe_works_on_executive_light_and_target_b`](../../../tests/unit/chrona/skills/test_chrona_skill.py) (passed here) checks the refusal, the three colours, the legend values, title and subtitle on both presets. Not hidden: the exact-main wheel documentation run of this guide failed on all three OS (the guide copies `executive-light` to `looks/executive-light` before the Skill page repeats it, `E_BUILTIN_PRESET_OUTPUT_EXISTS`); the correction is the open [PR #1788](https://github.com/tya5/chrona/pull/1788) and does not change what the recipe renders. | — |
| 4 | the message names the role and what to declare, or the preset declares the role (reviewer YAML). | met | The message names the role and what to declare. Reproduced: `executive-light` with a View that has a `subtitle` and a Theme without `roles.subtitle` is `rejected` with `E_THEME_ROLE_REQUIRED`: "the Theme declares no role 'subtitle', which this View needs (it was read for 'fontFamily'); declare roles.subtitle with its typography properties (fontFamily, fontSize, lineHeight, ...), for example by copying the 'heading' role (Spec 07; at /body/roles/subtitle)". No `bindingType=NoneType` remains. Test: [`test_a_subtitle_without_a_theme_subtitle_role_names_the_role_and_what_to_declare`](../../../tests/integration/test_deadline_mark.py) asserts the whole message (passed here). The guide says the same and shows the derived Theme that declares `roles.subtitle`: [`typed-fields.md`](../../guides/typed-fields.md), "Title and subtitle". The preset itself was not changed. | — |
| 5 | the error says that a parent path is not permitted and names the allowed form; the guide states it. | met | Reproduced: the guide's plan with `path: ../../profile.yaml` is `rejected` by `chrona validate` with `E_SCHEMA`: "expected one permitted form: ...; 'path' (/extensions/0/path): a parent directory ('..') is not permitted; write a relative path below the file's own directory, such as 'folder/file.yaml'". It names the refusal and the allowed form. Test: [`test_an_extension_path_with_a_parent_directory_says_so_and_names_the_allowed_form`](../../../tests/unit/chrona/test_schema_diagnostics.py) (passed here). Guide: [`typed-fields.md`](../../guides/typed-fields.md), section 2, states that a parent directory, an absolute path or a `.` segment is not permitted and to write `extensions/typed-team.yaml`, not `../../profile.yaml`. | — |

## Programme-level criteria (optional)

### Public side effects

This review adds one document and two PNG files only.

| Item | Routes | Labels | Primitives | New diagnostics |
| --- | ---: | ---: | ---: | ---: |
| This review (one document, two PNGs) | 0 | 0 | 0 | 0 |

Rows 1 and 2 stay with dev A; the issue stays open until its owner closes it after the release gate.
