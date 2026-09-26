# Architecture Review — Axis Lanes, Cells and Rule (#426 rows 5–10)

**Decision:** approved for implementation as slice I426-2. **Reviewed:** [correction](../../design/issue-426-axis-cells-correction-2026-09-27.md).

| Boundary | Result |
| --- | --- |
| View | No syntax change. The existing tiers, `unit` pairing and `typographyRole` are enough. |
| Theme v0.11 | Additive optional role properties `laneBlockSize`, `cellGap` and `labelInset`, plus two optional roles (`axis-rule`, `axis-cell-separator`), extended in place as in #430/#428/#427. |
| Layout | One axis pass with a declared-lane pre-pass; the legacy branch is untouched when nothing is declared, so bytes are preserved. |
| Scene / adapters | Paths and Rects with registered semantics; contrast and perceptibility gates apply. |
| Evidence | The axis rule adds one primitive to every public slide, deliberately. Presets change (they are not committed slides) and are covered by render tests. |

**Risk:** #467 and #479 also edit the preset Views (lanes, labels `both`). The axis tier edits do not overlap those fields, so a rebase is mechanical.
