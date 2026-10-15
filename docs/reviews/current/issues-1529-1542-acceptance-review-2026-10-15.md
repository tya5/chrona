<!-- chrona:literal-acceptance/v1 -->

# Acceptance review: technical-print lane columns (#1529) and column x accumulation (#1542)

Checked on `origin/main` `b86cb75bf` ("Regenerate public derived evidence"), which contains [PR #1541](https://github.com/tya5/chrona/pull/1541) (merge `639a7bd8`), [PR #1544](https://github.com/tya5/chrona/pull/1544) (merge `3e8519ca`) and the derived-sync bot commit that regenerated the three halcyon-1 Scenes. Issue bodies and comments were re-fetched on 2026-10-15 (`gh issue view 1529 --comments`, `gh issue view 1542 --comments`): #1529 has one "Needs" paragraph and no comments; #1542 has an acceptance line of three numbered conditions and two comments (the dev status question and the decision record). Nothing in `examples/**` was edited. This review closes neither issue by itself.

Commands run in a fresh worktree with a new `.venv` (`pip install -e '.[dev,render]' -e packages/chrona-fonts-noto-cjk`, as `.github/workflows/conformance.yml` does):

- `pytest tests/integration/test_technical_print_columns.py tests/integration/test_packaged_bounded_table.py tests/unit/chrona/presentation/layout/test_bounded_table_columns.py tests/integration/test_typeset_presets.py tests/integration/test_lane_table_columns.py`: 89 passed.
- `chrona render --preset technical-print -o a.svg examples/chrona-roadmap/project.yaml`: `status: ok`, no error diagnostics; the SVG contains the header texts `No`, `Task` and `Owner`.
- Pre-fix check: a detached worktree at `3e8519cae^` supplied `src` through `PYTHONPATH` (`chrona.__file__` confirmed to point at it) while the test files came from main. `pytest tests/integration/test_packaged_bounded_table.py -k fitting_packaged` failed: 1 failed (`test_fitting_packaged_copy_keeps_scene_surface_and_svg[technical-print]`, exact `after.surface == before.surface`), 9 passed. On main the same test passes.
- `python tools/regenerate_public_examples.py --check --jobs 4` on `b86cb75bf`: `Public materializers: PASS (50 slides)`. On the earlier `3e8519cae` (before the bot commit) the same command failed with `E_MATERIALIZER_MISMATCH`, which is the expected delta of #1542 row 2.
- Scene values on main: `examples/halcyon-1/generated/07-replan-baseline.scene.json` holds `854.08` (9 occurrences, no `854.0799999999999`); `06-flight-readiness.scene.json` holds `783.9163636363636` (25); `26-gates.scene.json` holds `1488.276` (12). No old digit string remains in any `*.scene.json`.

## Literal issue acceptance

### Issue #1529

- Source: [Issue #1529](https://github.com/tya5/chrona/issues/1529) (OPEN; one "Needs" paragraph, split below into its requirements; the sentence about the `1.` punctuation is a scope statement; no comments)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Declare columns `[rowIndex, label, {field: owner, transform: initials}]` in the bundled technical-print View. | met | [view.yaml](../../../src/chrona/resources/presets/bundles/technical-print/view.yaml) `rows.laneTable.columns`: `No` (`rowIndex`), `Task` (`label`), `Owner` (`{field: owner}`, `transform: initials`), lane `packing` unchanged. `chrona render --preset technical-print` shows the three headers (commands above); [test_technical_print_columns.py](../../../tests/integration/test_technical_print_columns.py) passed. | — |
| 2 | Golden and tests re-recorded, side-effect counts in the PR. | met | Tests: [test_technical_print_columns.py](../../../tests/integration/test_technical_print_columns.py) added, [test_packaged_bounded_table.py](../../../tests/integration/test_packaged_bounded_table.py) adjusted, both passed; [test_typeset_presets.py](../../../tests/integration/test_typeset_presets.py) passed. No golden file for technical-print is in the PR's file list. Side-effect table in [PR #1541](https://github.com/tya5/chrona/pull/1541): 0 of 50 public slides changed, 0 `examples/**` edits; the design note is [issue-1529-technical-print-columns-2026-10-15.md](../../planning/active/issue-1529-technical-print-columns-2026-10-15.md). On current main the public materializers pass for all 50 slides (commands above). | — |
| 3 | Mark gap 3 `lane-table-columns` of the technical-print gaps record resolved. | met | [technical-print-vocabulary-gaps.md](../../diagnostics/technical-print-vocabulary-gaps.md) row 3 reads "resolved (#1529)" and names the three columns; row 5 is also updated for the bold header (`tableColumnLabel` with `weight.bold` in the bundled [theme.yaml](../../../src/chrona/resources/presets/bundles/technical-print/theme.yaml); asserted by `test_technical_print_lane_table_columns_and_bold_header`). | — |
| 4 | "The numbering punctuation `1.` is out of scope of #1525 and is a separate gap if wanted." (reference also shows monospaced initials and a header rule). | narrowed | Not delivered ([technical-print-vocabulary-gaps.md](../../diagnostics/technical-print-vocabulary-gaps.md) rows 3 and 5): `rowIndex` renders the bare number; initials use the body face; no header rule. The gaps record row 3 lists "the `1.` punctuation (a separate gap), monospaced initials" as not reached and row 5 lists the header rule as not measured as expressible. The body itself places the punctuation outside this issue. | [Issue #1545](https://github.com/tya5/chrona/issues/1545) |

Verdict for #1529: rows 1 to 3 met, row 4 narrowed to #1545. #1529 can be closed on its literal acceptance; the owner closes it.

### Issue #1542

- Source: [Issue #1542](https://github.com/tya5/chrona/issues/1542) (OPEN; body acceptance line with conditions (1) to (3); two comments: the dev status and question, and the decision record accepting the three Scene deltas)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The exact-equality version of `test_fitting_packaged_copy_keeps_scene_surface_and_svg` passes for every packaged preset, including muted-executive at body size 14 and technical-print. | met | [test_packaged_bounded_table.py:79](../../../tests/integration/test_packaged_bounded_table.py) asserts `after.surface == before.surface` and equal SVG bytes with no rounding; passed for all identifiers on main (89 passed above). Fails on the pre-fix source for `[technical-print]` (pre-fix check above). The fix is the single accumulation in [PR #1544](https://github.com/tya5/chrona/pull/1544); [test_bounded_table_columns.py](../../../tests/unit/chrona/presentation/layout/test_bounded_table_columns.py) passed. | — |
| 2 | Public examples byte-identical, or the changed slides listed as expected deltas. | met | Changed slides listed on the issue and accepted in the decision record comment: halcyon-1 [06-flight-readiness](../../../examples/halcyon-1/generated/06-flight-readiness.scene.json) (25 values), [07-replan-baseline](../../../examples/halcyon-1/generated/07-replan-baseline.scene.json) (37), [26-gates](../../../examples/halcyon-1/generated/26-gates.scene.json) (12). Regenerated by the derived-sync bot commit `b86cb75bf`, not by hand; main now carries `854.08`, `783.9163636363636`, `1488.276`, and `regenerate_public_examples.py --check --jobs 4` passes for 50 slides. | — |
| 3 | The rounding in the test is removed. | met | The assertions at [test_packaged_bounded_table.py:79-95](../../../tests/integration/test_packaged_bounded_table.py) compare surfaces and SVG bytes directly; the "rounded to 6 decimals" helper added by PR #1541 is gone (`grep -n round` over the test finds none in that test). | — |

Verdict for #1542: rows 1 to 3 met; the comment thread asks for no further action. #1542 can be closed on its literal acceptance; the owner closes it.

## Programme-level criteria (optional)

None beyond the rows above.

## Architecture conclusion

Column positions now come from one helper (`column_inline_positions`) from the same absolute origin on both the wrapped and unwrapped paths, so layer ownership is unchanged and no preset works around the core. The technical-print change is data only (View and Theme). Remaining reference details are tracked in #1545. No issue is closed by this review commit itself.
