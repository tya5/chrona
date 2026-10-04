<!-- chrona:literal-acceptance/v1 -->

# Issue #1126: contrast constraints as an opt-in design option, acceptance review

Source: [Issue #1126](https://github.com/tya5/chrona/issues/1126), observed 2026-10-04. The body (unchanged since filing) proposed a Theme-declared per-pair acceptance with a reason against an always-on floor. The [owner decision](https://github.com/tya5/chrona/issues/1126#issuecomment-5975942320) of the same day, recorded on the issue, **supersedes that as the main mechanism**: enforcement is an opt-in design option, a Theme chooses a policy per class, the default is warning, and a reasoned acceptance stays only as an optional refinement under `error`. The six rows below are the six literal acceptance bullets of the body, each judged against what was built; the owner's own criteria are in the architecture conclusion. Work record: [issue-1126-contrast-opt-in-2026-10-04.md](../planning/active/issue-1126-contrast-opt-in-2026-10-04.md); living contracts [Specification 46](../../specification/46-completed-scene-paint.md) section 8, [50](../../specification/50-constraint-driven-gantt-surface-quality.md) section 3.4 and [07](../../specification/07-style-and-theme.md).

Slices: design [PR #1131](https://github.com/tya5/chrona/pull/1131) (`f5081df0`); O1126 [PR #1133](https://github.com/tya5/chrona/pull/1133) (`1cddee3e`).

## Literal issue acceptance

### Issue #1126

- Source: [Issue #1126](https://github.com/tya5/chrona/issues/1126)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A text pair at 3.72 with an acceptance at 3.5 gives a warning, not an error. The same pair with an acceptance at 4.0 gives an error. | narrowed | **The 3.72 pair is a warning, with no acceptance:** under the Theme default (`warning`) it is `W_SCENE_STATE_TEXT_CONTRAST`, and under the strict gate it is the error it was; a Theme that opts `stateText` or `groundText` into `error` blocks it ([`test_contrast_opt_in.py`](../../../tests/unit/chrona/presentation/scene/test_contrast_opt_in.py) `test_the_two_target_b_pairs_...`: white `#FFFFFF` on amber `#B8761F`, 3.717 against 4.5; [`test_contrast_opt_in_render.py`](../../../tests/integration/test_contrast_opt_in_render.py): a real render warns by default and `groundText: error` fails at `/body/contrastPolicy/groundText`). **Not built:** a declared `minimum` with its above-and-below behaviour, because the owner's decision replaced it. | [#1134](https://github.com/tya5/chrona/issues/1134) (optional reasoned per-pair exception; searched contrast acceptance, per pair, reason: no duplicate) |
| 2 | A mark pair at 1.0 with an acceptance at 1.0 gives a warning. | narrowed | The same-ink actual gate over the planned gate (1.000 against 3.0) is `W_SCENE_MARK_CONTRAST` under the Theme default and an error under the strict gate (the hand-built Scene of the same test in [`test_contrast_opt_in.py`](../../../tests/unit/chrona/presentation/scene/test_contrast_opt_in.py)). No acceptance entry exists. | [#1134](https://github.com/tya5/chrona/issues/1134) |
| 3 | Missing `minimum` or `reason` fails at its pointer. | narrowed | Not applicable: there is no acceptance entry to omit a member of. What is validated instead: every `contrastPolicy` member and value is checked by the schema (`E_THEME_SCHEMA`) and again at Theme resolution (`E_THEME_CONTRAST_POLICY`), each at its pointer `/body/contrastPolicy/<member>`, including the YAML trap where an unquoted `off` is the boolean false ([`test_color_scheme.py`](../../../tests/unit/chrona/presentation/test_color_scheme.py)). | [#1134](https://github.com/tya5/chrona/issues/1134) |
| 4 | An unmatched acceptance warns. | narrowed | Not applicable for the same reason. The consumer rule it followed holds for the new member: all five policy members are read by the render and the corpus tool, and an unknown member or value is refused rather than ignored (an unread binding cannot validate; [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py) `_resolve_severities`, [`color_scheme.py`](../../../src/chrona/presentation/color_scheme.py) `_contrast_policy`). | [#1134](https://github.com/tya5/chrona/issues/1134) |
| 5 | Absent declarations give byte-identical output. | met | A Theme with no `contrastPolicy` renders the same picture and Scene as one that declares every class `warning` (`test_ground_text_set_to_warning_equals_the_default_byte_for_byte` in [`test_contrast_opt_in_render.py`](../../../tests/integration/test_contrast_opt_in_render.py)), a policy changes diagnostics and never the picture (`test_the_policy_changes_only_diagnostics_never_the_picture`), and `python tools/regenerate_public_examples.py --check --jobs 4` passes for all 64 slides: every public Scene and SVG is byte-identical; the CLI characterization goldens pass unchanged. | none |
| 6 | Target B declares both pairs: the as-of label is white on the amber chip, and the overlaid actual gate passes with a warning. | narrowed | **No declaration is needed.** With PR [#1106](https://github.com/tya5/chrona/pull/1106) and PR [#1118](https://github.com/tya5/chrona/pull/1118) merged onto the O1126 `main` (a scratch merge, nothing committed) the regenerated target-B Scene reads, with `target-b` not opted in: 0 errors, `W_SCENE_MARK_CONTRAST` on the one overlaid `actual` gate, `W_SCENE_STATE_TEXT_CONTRAST` on the white `as-of-label`, and 79 `W_SCENE_DECORATION_CONTRAST` on the weekend stripes; the strict gate reads the two errors that blocked those PRs. The two PRs and the target-B YAML are the reviewer's and dev A's; they need a rebase onto `main`, not an edit. | [#1074](https://github.com/tya5/chrona/issues/1074) and [#1110](https://github.com/tya5/chrona/issues/1110) (open; they own PRs #1106 and #1118; no new issue needed) |

## Programme-level criteria (optional)

The owner's criteria, as built:

- A Theme that declares nothing is not blocked by contrast: met. Every class is `warning`, a typed warning in the render warnings, Scene `diagnostics`, CLI, MCP and the corpus report.
- A Theme may choose per class `none`, `warning` or `error`: met (`none` is spelled so because an unquoted `off` is a boolean in YAML 1.1); an opted-in `error` blocks the render with the blocking code.
- Bundled presets and shipped examples stay held to the floors: met by `conformance/contrast-opt-in.yaml`, not by editing the Themes (disclosed below); seven bundled presets opted into `error` for every class render a standard project with no floor miss.

## Architecture and release conclusion

Theme declares the policy per class; the render enforces it where the Theme is known; the completed-Scene evaluator takes the policy as an argument and reads no Theme; the corpus tool, which sees Scenes only, applies the repository's opt-in registry by each Scene's Theme provenance; Layout and adapters are untouched. Floors, structural checks (paint, treatment, malformed Scene, `E_THEME_ROLE_REQUIRED`) and the Theme-resolution text checks are unchanged and not governed. `theme-v0.11` and `theme-v0.13` gained the optional `contrastPolicy` members in place (Specification 56 section 3.2; `decoration` gained `none`, one expected-delta pair; three stale expected-delta entries of merged PRs were retired with `--prune-stale`); the S0 gate `python -m tools.schema_equivalence --base-rev origin/main` passed on the code PR with both schemas `additive`. No Theme, preset or example was edited; the target-B files were not touched. Mutation checks: 19 of 19 killed, one first-pass survivor recorded in the work record.

Disclosures:

- **The registry replaces editing the Themes.** The owner's note says bundled presets opt into `error`; opting 60 Theme files in by YAML would have changed every Theme and Context identity and every Scene's provenance (no repin tool) and contradicts the byte-identity requirement, so `conformance/contrast-opt-in.yaml` lists the Theme ids the repository holds to the floors. A user who runs a bundled preset gets warnings only. Decision and reversal are on the issue.
- **Optional floors are not built.** The owner's note allows optional floor values per class; a class is switched, not retuned. Additive later (an optional `floor` per member).
- **The per-pair acceptance is dropped**, as the note allows; #1134 holds the optional refinement.
- **A default render now reports a contrast miss it never reported** (marks and text were gated only in the corpus tool): no default CLI render in the characterization matrix changes, and none of the 64 public slides does.
- **Not listed means not held.** A new example Theme is unguarded until listed; the corpus report prints every unlisted Theme with its warning count so the drift is visible. `target-b` is deliberately unlisted (owner decision).

Exact review-bearing-main three-OS CI and the newest-Python materializer run must pass before closing #1126; that run is recorded in the closing comment.
