<!-- chrona:literal-acceptance/v1 -->

# Literal acceptance review: #1813 rows 1 to 4

Observed on `main` at `2350a3c4d` (the derived-sync ready tip). [Issue #1813](https://github.com/tya5/chrona/issues/1813) has four acceptance rows. Rows 1 to 3 and the README text of row 4 landed through [PR #1823](https://github.com/tya5/chrona/pull/1823) (merge `b5d780034`). The issue body was re-fetched with `gh issue view 1813 -R tya5/chrona --json body` on 2026-10-21 and counted literally: four numbered rows, each with one Acceptance line.

## Method

Private venv, `PYTHONPATH=<worktree>/src:<worktree>`, no editable install. Tests run: `tests/unit/tools/test_readme_guide_index.py` and `tests/integration/test_csv_import_guide.py` (5 passed). `python tools/check_documented_commands.py --check --execute` exits 0 with no output ([documented-commands.txt](assets-1813/documented-commands.txt)). The Quick start commands were then run by hand in an empty directory: `chrona init`, the SVG render, the PNG render at `--viewport 1600xauto` and `--viewport 3200xauto`, and the README's `resvg_py ... zoom=2` one-liner. The PNG sizes were read from the IHDR chunk ([widths.txt](assets-1813/widths.txt)). The full suite was not run. No `--scale` option exists and none was added.

## Literal issue acceptance

### Issue #1813

- Source: [Issue #1813](https://github.com/tya5/chrona/issues/1813)
- Observed: 2026-10-21

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | a "How do I…" table in the Quick start, checked by the docs link test. | met | [README.md](../../../README.md) has a `### How do I...` table inside the `## Quick start` section (heading at line 124, before `## Presentation slides`). [`test_readme_guide_index.py`](../../../tests/unit/tools/test_readme_guide_index.py) checks it: `test_every_guide_is_linked_from_the_readme`, `test_the_how_do_i_table_is_in_the_quick_start` and `test_readme_local_links_resolve` (passed here). | — |
| 2 | the recipe goes in csv-import (the `--role` section) or first-project, and runs in the docs tests. | met | [csv-import.md](../../guides/csv-import.md) has the `colour-the-bars-by-owner` recipe beside the `--role responsible=owner` import and the `colorEncoding` block. [`test_guide_colour_by_owner_recipe_runs_on_a_plain_csv`](../../../tests/integration/test_csv_import_guide.py) extracts the guide's CSV and recipe and runs them on a plain CSV (passed here). first-project links to it. | — |
| 3 | one paragraph in first-project that maps each to its file and member. | met | [first-project.md](../../guides/first-project.md) (line 60, "Which file do I edit?") maps title (`project.title` in `project.yaml`, or `heading.title` in `view.yaml`), colour (`colorEncoding` in `view.yaml`), legend position (order of the `legend` slot among `root.children` in `layout.yaml`) and window (`window` in `view.yaml`) in one paragraph. | — |
| 4 | a `--scale` (or equivalent) PNG option, or the existing way to get one, documented; plus the Today/asOf sentence in Quick start. | met | The existing ways are documented in the [README Quick start](../../../README.md) (lines 84 to 98) and both work. Measured PNG sizes, same plan ([widths.txt](assets-1813/widths.txt)): default `--viewport 1600xauto` is 1600 x 332 ([plan.png](assets-1813/plan.png)); `--viewport 3200xauto` is 3200 x 332, laid out afresh ([plan-3200.png](assets-1813/plan-3200.png)); `resvg_py` `zoom=2` on the SVG is 3200 x 664, layout kept ([plan@2x.png](assets-1813/plan@2x.png), from [plan.svg](assets-1813/plan.svg)). The README states "The PNG is 1600 px wide at 1x". The Today sentence is there too: the Today marker is drawn only with an Actual Set with `asOf` (`--actual`); the render with `--actual` has the `TODAY` label (2 matches in the SVG) and a render without it has none (0 matches). A literal `--scale` option was not added; the criterion allows the existing way. | — |

## Programme-level criteria (optional)

### Public side effects

This review adds documents and pictures only.

| Item | Routes | Labels | Primitives | New diagnostics |
| --- | ---: | ---: | ---: | ---: |
| This review (one document, three PNG, one SVG, two text files) | 0 | 0 | 0 | 0 |
