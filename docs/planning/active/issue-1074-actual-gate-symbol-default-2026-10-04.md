# Issue #1074: default actual gate symbol no smaller than the planned gate (work record)

Living record for [#1074](https://github.com/tya5/chrona/issues/1074), the successor of the narrowed row 4 of [#1066](https://github.com/tya5/chrona/issues/1066) (work record [issue-1063-1066-target-b-top-items-2026-10-03.md](issue-1063-1066-target-b-top-items-2026-10-03.md), acceptance review [issue-1066-symbol-size-acceptance-review-2026-10-04.md](../../reviews/current/issue-1066-symbol-size-acceptance-review-2026-10-04.md)). Baseline, literal acceptance, design plan, design, architecture review and implementation plan are published together before code. Edited in place; Git keeps history.

**Public base:** `3990b5fb` on `main`. **Status:** design published; no code yet. This is a **behaviour change** (a default changes), unlike the knob slices: the corpus is regenerated and reviewed grouped, with images.

**Scope rule (owner):** core only; the reviewer's `examples/halcyon-1/*target-b*` files are not edited (PR #1061 in flight). The generated target-B outputs change only through derived-sync, as every slide's do.

## 1. Published baseline

Read on `3990b5fb` from code and the committed Scenes:

1. A point mark (gate or milestone) of role R is a square of `markHeight(R)` x track at `markOffset(R)`; since #1066 the optional `symbolHeight` and `symbolOffset` tokens replace those two values for point marks only, each independently (`MarkGeometry.symbol_extent`, `MarkBandFrame.symbol_bounds`).
2. The `actual` role's band is a thin bar (executive: 0.6 of the track, halcyon 21-target-b: 0.17), so an actual gate is smaller than the planned gate in **every** committed slide that has one. Measured on the 55 committed Scenes that draw an actual gate: actual side against planned side is 4.8 / 8.0 (aster-ssd), 14.4 / 24.0 (controller-z and controller-z-ja slides), 6.0 / 10.0 (eleven halcyon-1 slides), 20.4 / 34.0 (the two halcyon-1 editorial slides), 14.0 / 36.0 (halcyon-1 technical print), 12.0 / 20.0 (orion-asic), 2.7 / 8.8 (halcyon-1 21-target-b). `gate-symbols` declares its own tokens and is the one slide that does not follow the rule.
3. Paint order puts `actual` in front of `planned` (`markPaintOrder`), so a same-size actual gate on the planned date hides the planned diamond; on a different date both show.
4. The mock draws one black diamond per gate.

Unverified (read per slice): which slides move labels, ports or icons because a mark's bounds grow.

## 2. Literal acceptance (copied from #1074)

| # | Criterion |
| --- | --- |
| A1 | Bundled Themes (or the Layout default) give an actual gate symbol at least the planned gate's size. |
| A2 | Actual bars keep their `markHeight`. |
| A3 | Corpus regenerated with a grouped diff review and images read (every slide with an actual gate changes). |
| A4 | Contrast and perceptibility gates still pass. |
| A5 | Synthetic tests with no `examples/` input; mutation check. |

## 3. Design plan

Use cases: **U1** any Theme with the usual thin actual band: the actual gate is as large as the planned gate and sits on it; **U2** a Theme that wants the old speck or any other size declares `symbolHeight` and `symbolOffset` on `actual` (equal to `markHeight` and `markOffset` to restore the old size exactly); **U3** a Theme whose actual band is already taller than the planned gate keeps its band.

## 4. Design (decisions; reverse = delete the default branch)

- **D1 where (Layout default, not Theme data).** The rule lives in `resolve_mark_geometries` (Layout), so every bundled and user Theme gets it without editing their data; the alternative, adding the two tokens to every bundled Theme, would copy one rule into eight resource files and leave user Themes behind. Reverse: one function.
- **D2 rule.** For the `actual` role only, an **absent** `symbolHeight` defaults to `max(markHeight(actual), symbol height of planned)` and an **absent** `symbolOffset` defaults, when the height was enlarged beyond the band, to the offset that centres the actual symbol on the planned symbol (`planned centre - height / 2`); otherwise (height not enlarged) it stays `markOffset(actual)`. A declared value always wins and is validated as before. The planned symbol size is the planned role's effective symbol extent (its `symbolHeight` or `markHeight`), so a Theme that sizes the planned gate carries the actual with it.
- **D3 scope.** Only the `actual` role. `snapshot` and `scenario` (baseline ghosts) are not changed: a ghost may be deliberately lighter or smaller, and the issue names the actual gate. `missing-actual` is span-only. Bars and open spans keep their band.
- **D4 restore.** Declaring `symbolHeight` equal to `markHeight` and `symbolOffset` equal to `markOffset` on `actual` reproduces today's size exactly; a test pins it.
- **D5 information loss disclosed.** A same-size actual gate on the planned date hides the planned diamond (paint order front); on different dates both are visible. A Theme can declare an actual symbol smaller than the planned one to keep both.

## 5. Architecture review

- **Layers.** Theme declares optional overrides; Layout owns the default and the geometry; Scene and adapters are unchanged. No Theme or schema property is added (the two properties exist since #1066), so no S0 run is needed; Specification 07 changes its sentence on the default.
- **Compatibility.** This is an intended output change for every slide with an actual gate. The migration is the D4 declaration.
- **Gates.** The enlarged symbol has the same paint, so contrast is unchanged; perceptibility only improves; checked on the regenerated corpus.
- **Residual risks.** Labels, ports and icons placed against the actual mark move when its bounds grow (read per group); lane subtracks and mark-aware scale insets read the composed mark and move with it (the provisional point facets use the same frame); an actual gate covering the planned one on the same date.

## 6. Implementation plan

| # | Slice | Owners (files) | Tests | Evidence |
| --- | --- | --- | --- | --- |
| 0 | This record (docs PR) | this file | conformance | none |
| 1 | Layout default | `layout/surface_marks.py` (`resolve_mark_geometries`), Specification 07 | synthetic: default size and centring, bars keep band, declared tokens win, restore declaration equals old bytes, band taller than planned keeps band, planned tokens carried, lane and automatic rows; mutation check | corpus regenerated by `regenerate_public_examples --write`, diffed by Scene, grouped by identical change with images read per group; unread slides listed |
| 2 | Acceptance review | `docs/reviews/current/issue-1074-*` | `tools/check_issue_acceptance_reviews.py` | exact-main three-OS run |
