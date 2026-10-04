<!-- chrona:literal-acceptance/v1 -->
# Issue #1114 — acceptance review

Source: [#1114](https://github.com/tya5/chrona/issues/1114), observed 2026-10-04.
Authority: [current design/review/plan](../../planning/active/issue-1114-primary-mark-repair-2026-10-04.md).
Evidence and per-context side effects: [PR #1138](https://github.com/tya5/chrona/pull/1138).
Head: `c3b857ece7db019b3a976b802ebce660082ad2a9`; [all PR checks passed](https://github.com/tya5/chrona/actions/runs/37201421690).

| Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- |
| start-to-at, and start-to-start, with the target to the right; | met | `test_relation_mark_safety.py::test_route_clears_own_and_foreign_marks_and_leaves_outward` | — |
| the mirrored end-to-end case with the target to the left; | met | Same neutral fixture, mirrored endpoints | — |
| a bar with no free gap above, and one with no free gap below. | met | `test_route_uses_open_side_when_foreign_bar_closes_above_or_below` | — |
| For each, no relation segment overlaps the interior of any bar by more than the stroke width, and the first segment leaves the port outward. | met | Neutral completed-path assertions; 59 focused tests passed | — |
| A Scene check counts own- and foreign-bar crossings corpus-wide; it must be 0 after regeneration. | met | 64 public Scene/SVG pairs: own 10→0, foreign 8→0; audit linked from PR | — |
| Existing compliant routes are unchanged. | narrowed | [Owner withdrawal](https://github.com/tya5/chrona/issues/1114#issuecomment-5979291651); accepted changes disclosed in PR | [#1109](https://github.com/tya5/chrona/issues/1109) |
| On target B, `avionics-cdr` no longer crosses the Avionics bar. | met | Actual Scene and SVG path verified; already-correct main baseline unchanged | — |

Architecture: Layout owns completed geometry and mark-interior checks; terminal
authorization covers only the outward stub. Scene observes; adapters serialize.
No schema, View, Theme, budget or project-specific rules change. No quality
mitigation or examples workaround is included.

Merged as `53227a5b76da8542d432d2ae8ec0d58409a51be1`. Final snapshot
is byte-identical to the audited snapshot across all 64 Scene/SVG pairs.
Release pending: exact-main three-OS evidence before closing.
