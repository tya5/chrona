# Design — Member Labels Stay in Their Own Row (#488)

**Plan:** [design plan](../planning/active/issue-488-member-label-row-band-design-plan-2026-09-27.md).

- **Placement region.** A member label's placement region is its own row band. The band spans the timeline's inline extent and the row's block extent. It is passed as the label request's `bounds`, the same field group-header point labels already use. `place_label` tests every candidate against it: the declared sides, the side-neighbourhood search and each rung of the declared fallback. A name therefore never reads as belonging to the adjacent row.
- **Chips.** A declared label chip (#428) is decoration around the text, so the region grows by the chip's padding. The text stays in the row, and its chip may reach past the band by its padding.
- **Fallback.** When no candidate fits, the declared ladder applies unchanged: `start`, then `suppress`. Each suppression is counted by the existing `I_LAYOUT_PLOT_LABELS_SUPPRESSED`.
- **Scope.** This is a placement-region rule of #466's model; there is no schema or Theme change. #467 lanes keep the rule, because a lane is the row band of its members.
