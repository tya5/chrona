<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review — #1658

Observed on `main` at `690f3549f` (contains [PR #1663](https://github.com/tya5/chrona/pull/1663) merge `1772a26fc` and its derived-sync bot commit `ec9d08748`). The criteria are copied from the #1658 body fetched on 2026-10-17 (`gh issue view 1658`): three rows. The twin tests were run on this base (`pytest tests/unit/chrona/presentation/scene/test_pattern_ink_mark_contrast.py`: 2 passed; `pytest tests/unit/chrona/presentation/scene -k contrast`: 235 passed). Trial 3 input is `trial3/project.yaml` from `dbbce45e60392b7b0be788f841fe2673f4830944`, rendered here with `chrona render project.yaml --preset sunday --output out.svg`. `tools/regenerate_public_examples.py --check` was not run in this environment (the editable install resolves schemas to another checkout); public counts were measured by diffing the committed files before and after the derived bot commit (`git diff aabc5e894 ec9d08748 -- examples`).

Delivering PRs:

| Issue | Developer PRs | Reviewer PRs |
| --- | --- | --- |
| #1658 | [#1663](https://github.com/tya5/chrona/pull/1663) (`contrast_policy._pattern_findings`: a patterned mark is judged by its ink against the ground) | none |

## Literal issue acceptance

### Issue #1658

- Source: [Issue #1658](https://github.com/tya5/chrona/issues/1658)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic twin: a hatch swatch whose ink passes 3:1 on the ground raises no `W_SCENE_MARK_CONTRAST`; a hatch whose ink equals the ground still does. | met | [`test_hatch_whose_ink_passes_on_the_ground_raises_no_mark_failure` and `test_hatch_whose_ink_equals_the_ground_still_fails`](../../../tests/unit/chrona/presentation/scene/test_pattern_ink_mark_contrast.py) pass on this base (2 passed). Rule stated in [Spec 46](../../specification/46-completed-scene-paint.md); code in [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py). | — |
| 2 | sunday on the trial 3 plan: no `W_SCENE_MARK_CONTRAST` on the key. | met | Rendered on this base: `chrona render project.yaml --preset sunday` returns status `ok`; the warnings are 55 `I_FONT_GLYPH_SUBSTITUTED`, 1 `I_LAYOUT_RELATION_POLICY_SUPERSEDED`, 1 `I_VIEW_FIELD_ROLE_UNBOUND`, 1 `I_VIEW_FIELD_GROUP_SUMMARIES_OMITTED`, all severity info, and no `W_SCENE_MARK_CONTRAST` at all. The key swatch is still drawn (`missing-actual` appears in the SVG). Resolvable record in the generated examples: `legend-swatch:missing-actual` was listed in [`roadmap-sunday.scene.json`](../../../examples/chrona-roadmap/generated/roadmap-sunday.scene.json) and [`25-sunday.scene.json`](../../../examples/halcyon-1/generated/25-sunday.scene.json) diagnostics at `aabc5e894` and is absent at `690f3549f` (also gone from [`roadmap-marquee.scene.json`](../../../examples/chrona-roadmap/generated/roadmap-marquee.scene.json) and [`24-marquee.scene.json`](../../../examples/halcyon-1/generated/24-marquee.scene.json)). Caveat, outside this row: `roadmap-sunday.scene.json` still carries two other `W_SCENE_MARK_CONTRAST` diagnostics (`planned:m1-gate:snapshot:m1-gate:part0`, `planned:tall-canvas:snapshot:tall-canvas`) and the two marquee scenes keep their `actual:*` gate-mark ones; those are different marks, not the key, and are not part of #1658. | — |
| 3 | Public SVG/Scene changes listed with counts. | met | Listed in the [PR #1663 body](https://github.com/tya5/chrona/pull/1663): 0 SVG, 4 Scene JSON (roadmap-marquee, roadmap-sunday, halcyon-1 24-marquee, 25-sunday; `W_SCENE_MARK_CONTRAST` diagnostic removed). Re-measured here: `git diff --stat aabc5e894 ec9d08748 -- examples` shows exactly those 4 files (1 line each) and no `.svg` file differs between `aabc5e894` and `690f3549f`. | — |

## Programme-level criteria (optional)

| Issue | Fully met | Open rows |
| --- | --- | --- |
| #1658 | 1, 2, 3 | none |

Public side effects, re-measured:

| Surface | Routes | Labels | Primitives | Diagnostics |
| --- | ---: | ---: | ---: | ---: |
| #1663: public examples (4 Scenes, 0 SVG) | 0 | 0 | 0 | -4 |
| This review (docs only) | 0 | 0 | 0 | 0 |

## Architecture conclusion

The false positive came from judging a hatch by its substrate colour alone; the rule now judges the strongest ink against the ground, while ink equal to the ground still fails. All three rows are met and #1658 may close after a green three-OS run containing this review. The remaining `W_SCENE_MARK_CONTRAST` diagnostics on gate marks in the public roadmap Scenes are separate and unticketed here.
