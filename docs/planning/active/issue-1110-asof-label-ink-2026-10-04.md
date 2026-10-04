# Issue #1110: as-of label ink, and bindings no primitive reads (work record)

Short work record for [#1110](https://github.com/tya5/chrona/issues/1110) (a local defect in one owner, so baseline, design and plan share this file). Edited in place; Git keeps history.

**Public base:** `d93c3687`. **Scope rule (owner):** the reviewer's `examples/halcyon-1/*target-b*` files are not edited (PR #1061 open).

## 1. Baseline (read on the code)

1. `semantic_registry.py` binds `asOfLabel` to the Theme role `text`; `emit_semantic_text("as-of-label", "asOfLabel")` painted it with `text`, so `as-of-label.fill` was never read. The legend labels had the same gap until #1062 (`legend.fill`, emitted with the role only when the Theme declares a fill).
2. The binding validated because `as-of-label` was an **unregistered** role name: `theme_role_property_consumer` falls back for unknown names to the open axis-tier and legend-swatch producers, and the legend fallback admits every Rect paint property (`fill`, `stroke`, ...). Any unknown role name with a paint property is therefore accepted without a consumer.
3. Audit of every Theme in `examples/*/themes`, the eight bundled preset Themes and the test fixtures, for role names that are neither registered nor `group:` names:
   - `as-of-label` (target B only): fixed here.
   - `table-cell-secondary` (controller-z `text-roles`): a View-named column role (#1062); read.
   - `annotation-text` (52 Themes: bundled presets and corpus), `table-header` (53), `range` (19): **accepted and never read**. Their only declarations are `annotation-text.fill`, `table-header.fill` and `range.fill`; no semantic binding, View `textRole`, axis tier or Detail Profile legend entry names them (annotation text uses `annotation-*-text`, headers use `text` or `tableColumnLabel`). Removing them edits every Theme and, through the pinned content identities, every Context: a separate corpus-wide change, filed as successor #1117.

## 2. Literal acceptance (copied from #1110)

| # | Criterion |
| --- | --- |
| A1 | With `as-of-label.fill` declared, the `as-of-label` Text carries that colour and is gated against the chip. |
| A2 | Without it, the output is byte-identical. |
| A3 | A fixture declaring a binding no primitive reads (for example `as-of-label.stroke`) produces the chosen diagnostic. |
| A4 | Target B: the as-of label is white on the amber chip. |

## 3. Design (decisions; reverse = delete the registration and the builder branch)

- **D1 honour.** The Scene builder paints the as-of label with the role `as-of-label` when the Theme declares `as-of-label.fill`, else with `text` as before (the `legend` pattern). The contrast gate resolves the label by its purpose as ground text, and a label with a chip is judged against the chip fill, so the gate sees the new ink on its chip.
- **D2 admit only what is read.** `as-of-label` is registered as a Theme role with the properties the label reads (`fill`, `opacity`) and Scene kind Text. Any other binding on it (`as-of-label.stroke`, `gradientStart`) fails at its pointer with the existing typed `E_THEME_ROLE_PROPERTY_UNSUPPORTED`. This closes the hole for this name; it does not close the open fallback for unknown names (D3).
- **D3 successor, not here.** The general check (every declared role name must have a consumer: registered, `group:`, or named by a View or Detail Profile) needs the unread names above removed from 50 Themes first, so it is the successor #1117 with the corpus-wide Theme edit; adding it now would fail or warn on every bundled Theme and move every Scene diagnostics list.
- **D4 target B (A4) and its contrast.** The knob works. Target B declares `asofInk #FFFFFF` on `asofChip #B8761F`: contrast 3.717 against the text floor 4.5. Since #1126 a Theme's contrast policy decides what a below-floor pair becomes (default warning, never blocking) and the repository holds only the Themes listed in `conformance/contrast-opt-in.yaml` to the floors; target B is not listed, so the pair is reported as one warning and blocks nothing. No floor and no gate is changed by this work.

## 4. Implementation plan

| # | Slice | Files | Tests | Evidence |
| --- | --- | --- | --- | --- |
| 1 | Honour and admit | `scene/v05_builder.py`, `scene/capabilities.py`, Specification 07 | `tests/integration/test_as_of_label_ink.py` (declared ink on the chip, gated; unreadable ink reported; byte identity; unread bindings fail at the pointer); mutation check | corpus regenerated: only `21-target-b` changes (the label ink), reported above |
| 2 | Acceptance review | `docs/reviews/current/issue-1110-*` | checker | exact-main three-OS run |

## 5. Addendum (reviewer, 2026-10-04): the label's own typography

The mock chip is 68 x 16 px with 10.5 px weight-600 text; target B's chip is 81 x 22.5 because the label takes `text` (12.5). Decision: the `as-of-label` role also admits the text measurement properties; with a `fontSize` it is the typography role of the as-of label (`as_of_label_typography_role`, one function read by the label request, the chip padding, the gap and the `below-plot` reservation), else `text` as before; a role that binds only a colour keeps `text`. Tests: the chip's block size and padding follow the role, a colour-only role changes no size, the space reserved below the plot equals the placed gap plus chip from the role's size; 5 of 5 mutations killed.
