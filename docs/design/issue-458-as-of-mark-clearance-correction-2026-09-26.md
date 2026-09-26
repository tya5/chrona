# Design correction — as-of fallback must clear data marks (#458)

**Predecessors:** [initial design](issue-458-as-of-label-suppression-design-2026-09-26.md),
[collision correction](issue-458-as-of-label-collision-correction-2026-09-26.md).

CI on `ee602340` exposed a real regression: on HALCYON 07, the first
visible-overflow candidate puts `as-of-label` over the planned Spacecraft AIT
bar. The #446 Scene gate does not classify text-over-mark; the independent
generated-output acceptance test correctly rejects it. The current generic
fallback rule chooses the first ranked candidate even when another location
can preserve the meaning without covering a data mark.

Decision: Layout's finite label request gains an optional *declared visible
fallback side* that must be one of its candidate sides. Ordinary labels keep
the first-candidate rule. The as-of request retains its beside-line candidate
ranking but adds an `above` candidate in the axis/timeline seam and declares
`above` as its fallback side. Its search bounds include the adjacent axis
region, so a collision-free seam placement is tried normally; if every
candidate fails, the `above` fallback remains mark-clear because its bounds
end before timeline marks begin. The completed Scene still carries the
timeline as-of identity and visible-overflow warning when applicable.

This is Layout-owned geometry policy, not Scene filtering or adapter
relocation. The acceptance output property of no text over marks remains a
release gate. Review all public as-of labels for newly moved placements and
do not rebaseline unrelated slides without design review.
