# Design Plan — Committed Slides for Unexercised Capabilities (#434)

**Public base:** `ae4cbaf6` on `main`. **Source of truth:** [Issue #434](https://github.com/tya5/chrona/issues/434) and its comments (the letter spacing, text transform and mono face row), Specifications 33, 38, 45 and 58.

## Published baseline (re-measured)

| # | Capability | Committed slide today |
| --- | --- | --- |
| 1 | row band spanning table and timeline | none. Only the default draft (`rowBand: both`, #483) draws spanning stripes, and it is not a committed slide. |
| 2 | `rowDistribution: fill` | none; every layout declares `pack` |
| 3 | `grouping.presentation: band` | none |
| 4 | a date column whose position does not move with a title | none; the title column is `minmax(content, …)` everywhere |
| 5 | non-default `every` in the coverage report | `orion-asic/gates` declares `every: 2`, but the report has no row for it |
| 6 | a leader styled independently of its box | none; every leader stroke equals its box's stroke |
| 7 | letter spacing, text transform, the mono face | none; every Theme uses 0 and `none`, and no slide measures with Noto Sans Mono |

Unreferenced example files: `aster-ssd/themes/onboarding-variation.yaml`, a derived-Theme example used by documentation and tests, and `controller-z/profiles/summary.yaml`. The four orphaned ASTER Views of the issue text were already removed by #441.

## Literal acceptance ledger

1. “Each of the six capabilities is rendered by at least one committed slide that reproduces byte-identically.”
2. “No view, theme or layout under `examples/` is unreferenced, or each is listed with a reason.”
3. “`presentation-coverage.md` names the slide that realizes a non-default `every`.”

The comment-added row (letter spacing, text transform, mono face) is treated as a seventh capability.

## Slices

- **I434-1 (tools):**
  - `presentation_coverage.py` lists non-default integer vocabulary, `every` among it;
  - `corpus_coverage.py` reports unreferenced View, Theme, Layout, Scheme and profile files, with a declared reason list.
- **I434-2 (slides):**
  - Controller Z `executive-light`'s callout leader gets its own treatment (item 6);
  - a new Controller Z `capabilities` slide with its own View, Layout and Theme copies (items 1–4 and 7).
- **I434-3:** acceptance review.
