<!-- chrona:literal-acceptance/v1 -->

# Release Review — Readable Defaults (#483)

**Reviewed product:** I483-1 `1e7c2882` ([slice review](issue-483-readable-defaults-i483-1-review-2026-09-26.md)) and I483-2 `a17f90c9`, on `main`. **Design:** [design](../../design/issue-483-readable-defaults-design-2026-09-26.md), [architecture review](issue-483-readable-defaults-architecture-review-2026-09-26.md). I483-2 depended on #481, which is now closed. This review also serves as the I483-2 slice review.

## I483-2 evidence

- **Default-draft View:**
  - `backgroundDecoration.rows: alternate`;
  - `labels.side: end` with fallback `[end, start, suppress]`, the tuned presets' configuration.
- **Briefing Layout:** `backgroundExtents.rowBand: both`. Its four committed slides (`01`, `06`, `08`, `09`) draw no row stripes, so they change only provenance. The structural diff shows no primitive changes, and no SVG bytes changed.
- **Test:** [`test_default_draft_guides_every_bar_across_the_plot_and_names_it_at_its_end`](../../../tests/integration/test_readable_defaults.py):
  - every stripe reaches the plot's right edge;
  - every row is striped or shares an edge with a stripe;
  - 20 of 28 member labels sit at their bar's end inside their own row.
- **The remaining 8 are measured, not hidden.**
  - 3 (`frr`, `mission-closeout`, `first-light`) take the declared start fallback inside their own row, because the end runs off the plot edge.
  - 5 (`optics`, `bus-test`, `cdr`, `launch`, `leop`) are displaced out of their row by the side-neighbourhood search that avoids dependency strokes. Confining that search to the row is a placement-model rule owned by #466's general placement, so it is filed as [#488](https://github.com/tya5/chrona/issues/488) rather than patched locally.
- **Visual check:** a PNG of the default draft shows stripes crossing table and plot, and names at the bar ends, with the exceptions above.

## Literal issue acceptance

### Issue #483

- Source: [Issue #483](https://github.com/tya5/chrona/issues/483)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The default draft and the shipped Themes draw a visible boundary between the axis and the plot: a rule, a band colour distinct from group bands, or both. A mechanical check compares the axis band's paint with the group bands'. | met | [I483-1 review](issue-483-readable-defaults-i483-1-review-2026-09-26.md); [axis-band tests](../../../tests/integration/test_readable_defaults.py). | — |
| 2 | The default draft gives every bar a row guide across the plot, a stripe or a rule, and a name at its end in its own row. | narrowed | Every bar has a stripe guide across the plot, and names are declared at the end with the presets' fallback. 20 of 28 are at the end in their own row; 5 are displaced out of their row by the side search ([default-draft test](../../../tests/integration/test_readable_defaults.py)). | [#488](https://github.com/tya5/chrona/issues/488) |
| 3 | `relationSourceTerminal` defaults to a circle or no mark in every shipped Theme. Committed evidence is regenerated. | met | [I483-1 review](issue-483-readable-defaults-i483-1-review-2026-09-26.md); [source-terminal tests](../../../tests/integration/test_readable_defaults.py). | — |
| 4 | `print-mono` renders slips and as-of distinguishably in greyscale. | met | [I483-1 review](issue-483-readable-defaults-i483-1-review-2026-09-26.md); [greyscale test](../../../tests/integration/test_readable_defaults.py). | — |

## Programme-level criteria (optional)

- CI: [four-job CI run 36250719502](https://github.com/tya5/chrona/actions/runs/36250719502) on `6ec9a1e2` (contains I483-2 `a17f90c9`), green.

## Architecture conclusion

- YAML, the default-draft configuration, and tests only.
- The one remaining gap, member-label row containment during side search, is a Layout placement-model rule and is tracked by #488 under #466's model.

Release disposition: rows 1, 3 and 4 are met; row 2 is narrowed with successor #488. #483 can close with a closing comment naming row 2 and #488.
