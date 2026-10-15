# Issue 1542: one accumulation for table column x

## Root cause

`place_table_columns` (`layout/presentation.py`) is the only column placer, but the x each
caller ends up with came from two different float accumulations:

- Unwrapped (no source closure): `surface_table.py` passes `bounds[0] = float(table.inline) + group_tag`
  and the placer runs `cursor += width + gutter` from that absolute origin, so
  `x2 = ((origin + tag) + w1) + gutter`.
- Wrapped (source-closed bounded table): `table_measurement.py` places from origin `reserved_inline`
  and `surface_table.py` later adds `float(table.bounds.inline) + item.inline`, so
  `x2 = origin + (tag + (w1 + gutter))`.

Float addition is not associative, so identical widths give x values one unit apart:
muted-executive body 14 `475.06533333333334` against `475.0653333333334`; technical-print lanes
`125.80600000000001` against `125.806`. #1541 hid it by rounding the test to 6 decimals.

## Fix

`column_inline_positions(origin, widths, gutter)` returns each x as one correctly rounded
`geometry_sum` (the Layout-owned `fsum`) over `origin, w1, gutter, w2, ...`. Both
`place_table_columns` and the source-closed branch in `surface_table.py` call it with the same
absolute origin (`table_bounds[0]`) and the same widths, so x depends only on origin and widths.
Widths are untouched. The rounding in `test_fitting_packaged_copy_keeps_scene_surface_and_svg` is removed.

## Scope

Core table measurement/placement only; no annotation, heading, mark, terminal, surface decoration or
Marquee code. Public examples are checked with `regenerate_public_examples.py --check`; any change
is reported in the PR side-effect table and `examples/**` is not edited. No performance claim.

## Public example effect (needs reviewer decision)

With the fix, `regenerate_public_examples.py --check` reports a Scene mismatch on three
`examples/halcyon-1/generated/*.scene.json` files; the last float digit of some column x values
moves toward the exact sum (SVG bytes not affected in the regeneration check). No geometry moves
by more than one float unit.

| slide | scene values changed |
| --- | --- |
| 06-flight-readiness | 25 (e.g. 783.9163636363635 to 783.9163636363636) |
| 07-replan-baseline | 37 (e.g. 854.0799999999999 to 854.08) |
| 26-gates | 12 (e.g. 1488.2759999999998 to 1488.276) |

`examples/**` is reviewer-owned, so this branch is not published until the reviewer accepts the
regeneration of those three files (recommended) or chooses a variant that keeps them byte-identical.
