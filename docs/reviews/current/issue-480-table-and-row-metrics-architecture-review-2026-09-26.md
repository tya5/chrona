# Architecture Review — Table and Row Metrics (#480)

**Decision:** design approved for implementation planning. **Reviewed design:** [#480 contract](../../design/issue-480-table-and-row-metrics-design-2026-09-26.md). **Evidence:** [prototype evidence](../../research/presentation/issue-480-table-and-row-metrics-prototype-evidence-2026-09-26.md). **Normative update:** Specification 24 §2.1. This is a design review, not issue acceptance.

## Whole-system consistency

| Boundary | Authority checked | Result |
| --- | --- | --- |
| View | Specification 24 §1, View `tableColumns`, the #403/#404 correction | No new syntax. View still owns column intent (`width`, `align`, `format`); the cell role still derives from `format`, now through one named function instead of a closure. |
| Theme | Specification 07 §5.1, `resolve_theme_metrics` | No metric added, removed or renamed. `table.column.minInlineSize` keeps its effective behavior, now stated as a slot floor. `paddingBlock` is stated as total padding, matching the code. The 14 Themes that bind these metrics are unchanged. This avoids contact with #478 I478-3's Theme resource migration. |
| Use case / Layout | Specifications 33 and 43; `usecases/render_review.py` | The use case normalizes typed table content earlier and passes it unchanged; it measures nothing. Measurement and placement call one Layout function, so the slot and its columns cannot disagree. Only the detail profile still needs the Layout manifest. |
| Row path / #467 | Specification 38 §3 and §3.1, `required_row_block_extents` | The text requirement is one extra input to the existing function. The probe and placement share it. #467 lanes (other session) extend the same function and must pass the same `text_line_block`; this is stated in the implementation plan and in the #480 comment, so a rebase is mechanical. |
| Draft `auto` / profile growth | Specification 50 (content requirement before placement) | Fixed by construction: the probe uses the same requirement. The prototype's density and mark-overflow findings came from a placement-only rule. |
| Scene / adapters | Specification 08 | Scene receives completed text boxes and baselines; nothing new to project. No adapter change. |
| Plot labels / #466 | Specification 50 label search | Not row-held; no interaction. |

## Reviewed ambiguities and resolutions

1. **`min: content` versus `content`.** The literal criterion concerns `inlineSize: content`. The prototype shows that correcting `min_inline` changes additive flex allocation on 18 slides. That changes the meaning of a content minimum in the engine and is a separate design. It is excluded here and filed as [#487](https://github.com/tya5/chrona/issues/487), not left silent.
2. **Floor versus retirement of `table.column.minInlineSize`.** Retirement would remove a required metric from 14 Themes, change one public slide (`11-overlay-briefing` shrinks from 630 to 384 px) and collide with #478's Theme migration. The floor keeps current bytes and satisfies the criterion ("never narrower"). The behavior is stated normatively, so it is not dead.
3. **Loader diagnostic versus Layout derivation.** Only Layout knows the cell roles in use. Derivation meets the first alternative of criterion 2.
4. **Cell centring changes public bytes.** This is intended. The old baseline ignored line height and role, so the requirement and the placement could not agree. The shift is a few pixels, with no geometry or warning change. It is accepted as an intentional output change, inspected visually in the slice review.

## Risks and gates

- **Hierarchy indent:** it may widen a hierarchy column on some slides. The batch diff must attribute every changed table width to either the indent or a defect.
- **Byte batch:** slice 2 must change only cell text coordinates. Any row-geometry change in a public slide means a Theme row is already smaller than its text, which must be reported in the slice review.

No unresolved user choice remains.
