# I483-1 Review — Axis Band, Source Terminal, `print-mono`, As-of Dash

**Implementation:** `1e7c2882` on `main`. **Public base:** `6f99571f`. **Design and plan:** [#483 design](../../design/issue-483-readable-defaults-design-2026-09-26.md), [implementation plan](../../planning/active/issue-483-readable-defaults-implementation-plan-2026-09-26.md). This is a slice review; #483 stays open for I483-2 (row guides, after #481). The slice also completes #423.

## Evidence and byte review

- **Source change, YAML only:**
  - nine corpus Themes: axis band `neutral` at opacity 1, and a circle source terminal. Controller Z `executive-light` already had its circle; `onboarding-variation` inherits both from ASTER `executive-light`.
  - every corpus and bundle Theme: `dash: dash.as-of` (`[4, 3]`) on `as-of`/`asOf`;
  - `print-mono` Scheme: `negative #000000`, `warning #444444`.
- **New tests:** `tests/integration/test_readable_defaults.py` has 39 cases, of which 31 fail on `6f99571f` and all pass after. They check:
  - the axis band against every group and row band in all committed Scenes, the default draft and the five presets (composited WCAG contrast ≥ 1.15);
  - the source terminal shape of every shipped Theme, including inheritance;
  - that no committed relation starts with its target arrowhead;
  - that `print-mono` variance states are separable in greyscale, the as-of line is dashed and the gridlines are solid.
- **Deviation from the design's test wording:** the design said the variance states differ "by at least 0.1 in relative luminance". Black versus `#555555` differs by 0.09 but has a WCAG contrast of 2.8, which is clearly separable. The test therefore requires a pairwise contrast ratio of at least 2, which is stricter in meaning and correct for dark greys.
- **Public materializers:** all 21 regenerated, then `--check` PASS. A structural comparison of every changed Scene shows paint and marker changes only, and no primitive bounds, path or diagnostic change:
  - `axis-band-rect` fill on 19 slides;
  - `relation.markerStart` on 14 slides (not on Controller Z slides that already had circles);
  - `as-of` dash on 16 slides (slides without an as-of line are unchanged);
  - `print-mono` stroke and cell fills on `03-launch-campaign` and `09-gallery-mono`;
  - `05-dependency-network` and `10-gallery-network-wallboard` change only provenance identity (their Theme bytes changed).
- **Rendered check:** PNG crops of `01-mission-brief` (light), `09-gallery-mono` (mono) and `08-gallery-dark` (dark) show the axis band ending visibly above the plot, a dashed as-of line among solid gridlines, and small circles at relation sources.
- **Generated reports:**
  - `presentation-contrast.md`: paint values only; the contrast gate passes.
  - `presentation-coverage.md`: `dashPattern` is now realized on 21 slides.
  - `diagnostics/inventory.md`: unchanged.
- **Tests and conformance:** full `pytest` and `run_conformance.py` locally (see the CI line).

## Architecture review

No code, schema, View or Layout change. Each item uses existing Theme vocabulary (`opacity`, `marker`, `dash`) and one Scheme's palette. Layout completes source-terminal geometry from the marker token as before. Scene carries `dash`, and the SVG adapter serializes it. The contrast gate covers the darker axis bands for axis text.

## Literal Issue #483 disposition after this slice

| # | Literal acceptance criterion | State | Evidence / next unit |
| ---: | --- | --- | --- |
| 1 | The default draft and the shipped Themes draw a visible boundary between the axis and the plot: a rule, a band colour distinct from group bands, or both. A mechanical check compares the axis band's paint with the group bands'. | met | band colour; `test_public_axis_band_is_distinct_from_group_and_row_bands`, `test_default_draft_and_presets_draw_a_distinct_axis_band`. |
| 2 | The default draft gives every bar a row guide across the plot, a stripe or a rule, and a name at its end in its own row. | not met | I483-2, after #481. |
| 3 | `relationSourceTerminal` defaults to a circle or no mark in every shipped Theme. Committed evidence is regenerated. | met | `test_every_shipped_theme_starts_relations_with_a_circle_or_no_mark`; 14 regenerated slides with changed source terminals. |
| 4 | `print-mono` renders slips and as-of distinguishably in greyscale. | met | `test_print_mono_separates_slips_and_as_of_in_greyscale`; `09-gallery-mono` PNG. |

[Four-job CI run 36244923666](https://github.com/tya5/chrona/actions/runs/36244923666) on `34f7c7ea`, which contains `1e7c2882`, is green: Ubuntu, Windows and macOS conformance/full pytest/wheel, and newest-Python public materializer reproduction. The run on `1e7c2882` itself was cancelled by the next push's concurrency group after three jobs passed.

I483-1 is accepted.
