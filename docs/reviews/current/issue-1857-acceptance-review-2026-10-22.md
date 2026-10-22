<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1857 rows 1 and 2

Observed on `main` at `734483472`. [Issue #1857](https://github.com/tya5/chrona/issues/1857) has one `Acceptance:` list with two bullets, counted here as rows 1 and 2. The body and its one comment (the "Merging #1861 now" note) were re-fetched with `gh issue view 1857 -R tya5/chrona --json body,comments` on 2026-10-22 and counted literally: two rows, none added since the issue was opened. Landed: [PR #1861](https://github.com/tya5/chrona/pull/1861) (merge `e110e5037`), which adds `viewDefaults.columnStyles.facet` with `format: signedDays` to nine bundled preset Layouts, including `editorial-readable-default` (the Layout of the CLI default `chrona-default-draft`), and rewrites the guide sentence. `editorial` is left out on purpose: its Layout must equal the HALCYON-1 corpus copy (`test_public_preset_evidence`).

## Method

Venv inside a fresh worktree on `origin/main` `734483472` (`pip install -e '.[dev,render]' -e packages/chrona-fonts-noto-cjk`). Inputs are the #1842 row 4 files, used unchanged from [assets-1842/row4](assets-1842/row4/view-no-format.yaml): `plan.yaml`, `baseline.yaml`, `actual-b-day-before.yaml`, `profile.yaml` and `view-no-format.yaml` (a View whose `Delta` column is `source: {facet: finishDelta}` with no `format`). The script is [run.sh](assets-1857/run.sh); its full output, with every command, is [render.log](assets-1857/render.log). The Delta cells were read from `--emit-scene` and from the SVG text. Focused tests: [pytest-1857.txt](assets-1857/pytest-1857.txt) (`test_update_a_plan_guide.py`, `test_public_preset_evidence.py`, `test_view_defaults.py`: 73 passed, none skipped). The full suite was not run.

## Literal issue acceptance

### Issue #1857

- Source: [Issue #1857](https://github.com/tya5/chrona/issues/1857)
- Observed: 2026-10-22

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | the edit lands and the bundled default draws `+6d*` for an unformatted Δ column; | met | The proposed line is on `main`: [`editorial-readable-default/layout.yaml`](../../../src/chrona/resources/presets/bundles/editorial-readable-default/layout.yaml) line 8 is `viewDefaults: {columnStyles: {facet: {format: signedDays, missing: blank, align: end, width: content, headerOrientation: horizontal}}}`. `chrona render plan.yaml --snapshot baseline.yaml --actual actual-b-day-before.yaml --forecast --view view-no-format.yaml` with no `--preset` (the bundled default `chrona-default-draft`) draws the Delta cells `+6d*` and `+2d*`, in the Scene and in the SVG text ([default.svg](assets-1857/default.svg), [log](assets-1857/render.log)); the same plan drew `6*` and `2*` on `2350a3c4d` ([#1842 row 4 log](assets-1842/row4/row4-small-items.txt)). The other eight edited presets draw `+6d*` / `+2d*` too (executive-light, elevated-light, technical-print, muted-executive, wallboard-dark), or `+6d` without `--forecast` for mission-light, control-room-dark and print-mono, which reject `--forecast` with `E_FORECAST_PRESENTATION_REQUIRED` (no legend slot; unrelated to this change). `editorial` still draws `6*` / `2*` ([editorial.svg](assets-1857/editorial.svg)), as PR #1861 declares and the guide now says. | — |
| 2 | the public slides that use the default preset are counted before and after (expected 0 of 50 change, per the #1842 comment), and the guide sentence "draws the bare number" is updated. | met | Count: 0 of 50 public slides changed. PR #1861 edited no file under `examples/`, its derived preview reported zero changed declared artifacts (merge note on the issue), and the serialized derived sync for `e110e5037` produced no bot commit: the next first-parent commit, `9d6e31a90`, has `e110e5037` as its parent, and `derived-main` on `e110e5037` is `completed`/`success` ([run](https://github.com/tya5/chrona/actions/runs/39520010879/job/118961269276), [log](assets-1857/public-count.log)). The tree holds 50 generated public SVGs before and after; all 50 are counted, a superset of the slides that use the default preset. Guide: [`update-a-plan.md`](../../guides/update-a-plan.md) section "A Δ column of your own" now says an unformatted column takes the design's `facet` column style, that the bundled presets except `editorial` declare `format: signedDays` (`+5d*`), and that "a design of your own without that style draws the bare number (`5*`)"; the diff is in the [log](assets-1857/render.log). `test_update_a_plan_guide.py` passed ([log](assets-1857/pytest-1857.txt)). | — |

Counts: 2 rows, 2 `met`, 0 `narrowed`, 0 `not met`.

## Programme-level criteria (optional)

### Release gate

The merge note on the issue also asks for the exact-main three-OS release run. That is not a literal row; it is the run on the `main` commit that publishes this review, to be cited when the issue is closed.

### Public side effects

This review adds a document and the files under [assets-1857](assets-1857/render.log); it changes no code, schema, specification, guide, preset or example.

| Item | Slides changed | New diagnostics | Schema delta |
| --- | ---: | ---: | --- |
| This review | 0 | 0 | none |
| PR #1861 | 0 of 50 | 0 | none |
