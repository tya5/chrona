<!-- chrona:literal-acceptance/v1 -->

# Issue #1582 — in-progress Actuals

Source `056d68e28849d64f4652b74bac3cffb98992e949`, ready base
`6ae0ccd80ed8b7b5e05a0edfbc09d2ef3f9113a1`.
[Published design/implementation record](https://github.com/tya5/chrona/issues/1582#issuecomment-6203648318).
Local acceptance below is complete; PR snapshot and exact-main three-OS
release remain required before closure.

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

Import the unmodified issue CSV with `chrona import --help`'s CSV syntax,
`--calendar 'standard mon-fri' --as-of 2026-10-16`; render its Project and
Actual-set with `chrona render project.yaml --actual actual.yaml --out result.png`
and each named preset. The initial default has no `--preset` argument.
Scratch evidence: `/tmp/chrona-1582-outsider.0WCfT8/final-*.png` and
`final-*.scene.json`; public snapshot and representative rasterizations:
`/private/tmp/chrona-1582-verify-agent/`. These are local verification aids,
not public release evidence; CI uploads the authoritative final snapshot.

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
