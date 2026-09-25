# Design Correction — Table Declaration Shape (#404, #403, #388, #389, #409)

**Status:** Accepted correction to the P1 design.

The proposed `table: {hierarchyColumn, columns}` wrapper adds no ownership,
validation, or reuse boundary over the existing View-owned `tableColumns`
array. It would make every View noisier solely to carry one peer field.

View v0.16 therefore retains `tableColumns` as the ordered table declaration
and adds optional top-level `hierarchyColumn`. Each `tableColumns[]` item gains
the designed `align` and `width` properties. All invariants and allocation
rules in the P1 design are unchanged: `hierarchyColumn` names a column ID,
not a position; Layout owns measured widths; and no compatibility reader is
retained for v0.15.

This is a contract-shape correction only. It preserves the intended clean
boundary while avoiding an unmotivated nesting layer.
