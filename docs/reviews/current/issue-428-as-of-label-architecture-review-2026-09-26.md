# Architecture Review — As-of Label Content and Label Chips (#428)

**Decision:** design approved for implementation planning. **Reviewed design:** [#428 design](../../design/issue-428-as-of-label-design-2026-09-26.md).

| Boundary | Authority | Result |
| --- | --- | --- |
| View | Specification 06; one current View version | v0.23 changes the default meaning of `label`, adds an optional `date` form, and migrates all Views atomically. The published #466/#467 designs that named v0.23 will renumber on landing; a coordination note goes on #467. |
| Axis vocabulary | Specification 39, axis name tables | Reused `localized-date` formatter; no new date forms. |
| Theme | Specification 07 | New role names by purpose (`*-chip`) plus one property (`chipPadding`); additive in v0.11. #478's admission registry (other session) must admit `*-chip` roles. |
| Layout | Specification 50 | Chip geometry and inflated footprint are Layout-owned; generic over purposes. |
| Scene / adapters | Specifications 08 and 63 | A Rect primitive; contrast via existing composited-ground analysis. |

**Risks:**
- Localized dates change the text on every slide with an as-of label. The batch must show only as-of-label text and width changes, plus any label re-placements they cause, each attributed.
- The ja-JP date format comes from the axis name table. It is verified on Controller Z-ja.
