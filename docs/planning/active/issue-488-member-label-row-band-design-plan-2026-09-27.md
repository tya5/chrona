# Design Plan — Member Labels Stay in Their Own Row (#488)

**Public base:** `adaf5afc` on `main`. **Source of truth:** [Issue #488](https://github.com/tya5/chrona/issues/488); #466 (general placement model, C2 landed); #483 (the default-draft readability goal).

## Reproduction

On the HALCYON-1 default draft, 5 of 28 member labels leave their own row: `optics`, `bus-test`, `cdr`, `launch` and `leop`. `place_label`'s finite side-neighbourhood search shifts a blocked candidate tangentially by up to one label height (`layout/labels.py`). The only region it checks is the whole timeline slot.

## Literal acceptance ledger

1. “A member label placed in the plot never leaves its own row band. If no candidate fits inside it, it takes the declared fallback (start, then suppress), and the suppression is counted.”
2. “The HALCYON-1 default draft places every member label at its bar's end or start inside its own row, or reports it suppressed.”
