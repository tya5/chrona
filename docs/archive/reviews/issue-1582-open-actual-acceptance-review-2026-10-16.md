<!-- chrona:literal-acceptance/v1 -->

# Issue #1582 — in-progress Actuals

Released through [PR #1591](https://github.com/tya5/chrona/pull/1591).
Final source `e06ad8519d6072d03259a8265914b5a1eb0c82bd` passed
[PR CI38823725828](https://github.com/tya5/chrona/actions/runs/38823725828);
artifact `12014360721` matches all 109 independently audited output/report paths.
Exact review-containing main `153d7ba155f61c52e6c1e232ae36c5f03778eb15`
passed [three-OS release38825302918](https://github.com/tya5/chrona/actions/runs/38825302918).
[Published design/implementation record](https://github.com/tya5/chrona/issues/1582#issuecomment-6203648318).
All literal acceptance rows and release gates are met.

## Literal issue acceptance

### Issue #1582

- Source: [Issue #1582](https://github.com/tya5/chrona/issues/1582)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: in-progress before and after the planned end; progress 0, 0.6, 1.0 without `finish`; no `start` still warns. | met | [Integration tests](../../../tests/integration/test_actual_in_progress_semantics.py) cover all cases, known late delta, blank not-yet-due delta and missing-start warning. [Model tests](../../../tests/unit/chrona/presentation/model/test_actual_observation.py) retain no fabricated finish. Final ready-base focused batch: 85 passed. | — |
| 2 | The CSV below renders both in-progress bars with their progress in the default draft, `executive-light`, `target-b` and `sunday`, viewed as PNG. | met | Exact [issue CSV](https://github.com/tya5/chrona/issues/1582), imported with standard mon-fri calendar and as-of 2026-10-16; independently viewed final PNGs for all four presets. Database schema and Component library each have an Actual start-to-as-of bar and 60%/30% progress, respectively; late delta +1d and not-yet-due delta blank. Reproduction commands below. | — |
| 3 | Public SVG/Scene changes are listed with counts in the PR (the committed examples have in-progress observations). | met | One complete 50-slide [snapshot workflow](../../../tools/derived_workflow.py): 43 SVG, 45 Scene and 4 reports changed; no added/retired paths. Per-slide count inventory is supplied in the publication PR. Full-record comparison: all 559 dependency paths, 28 annotation leaders, 11 network edges and 113 relation labels unchanged. Representative public SVGs rasterized and visually checked. | — |

## Programme-level criteria (optional)

Verification commands (project-local venv):

```sh
.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_surface_quality.py tests/unit/chrona/presentation/scene/test_multipart_mark_contrast.py tests/integration/test_actual_in_progress_semantics.py tests/integration/test_design_presets.py
.venv/bin/python -m tools.derived_workflow snapshot 6ae0ccd80ed8b7b5e05a0edfbc09d2ef3f9113a1 derived-snapshot.tar.gz
```

For the unmodified issue CSV saved as `plan.csv`, use a fresh output directory:

```sh
.venv/bin/chrona import plan.csv --output project.yaml --actual-output actual.yaml --calendar 'standard mon-fri' --as-of 2026-10-16
.venv/bin/chrona render project.yaml --actual actual.yaml --output draft.png
.venv/bin/chrona render project.yaml --actual actual.yaml --preset target-b --output target-b.png
```

Repeat the named-preset command for `executive-light` and `sunday`; view all four
PNGs. Public final-head snapshot evidence is attached to the PR CI run above.

Architecture: shared model classification/delta; Layout completes open-span
and multipart progress geometry and explicit logical ownership. Scene/adapters
are unchanged. Existing members are Actual `start`/`progress`, comparison
`missingActualScope`, variance `missingBy.inProgress`, and `progressFill.source`.
No schema change or corpus edits. Stroke-only point glyphs have no fillable
interior. The five shared designs explicitly select Actual progress and blank
not-yet-due variance; authored View policy still overrides defaults.

Diagnostic delta: 13 retired `W_LAYOUT_ACTUAL_INCOMPLETE:tvac`, 6 retired
missing-mark contrast warnings, 2 existing no-cutoff cases now explicitly
`W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:performance`. Internal same-slot host
invariant `E_LAYOUT_SHAPE_HOST_INVALID` is inventoried, never emitted here.
Contrast errors remain zero. Working-day dates (#1583), hierarchy grouping
(#1584), and existing CSV contrast/routing warnings are not represented as fixed.
