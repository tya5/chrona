<!-- chrona:literal-acceptance/v1 -->
# Issue #1114 — acceptance review

Authority: [archived design/review/plan](../planning/issue-1114-primary-mark-repair-2026-10-04.md).
Evidence and per-context side effects: [PR #1138](https://github.com/tya5/chrona/pull/1138).
Head: `c3b857ece7db019b3a976b802ebce660082ad2a9`; [all PR checks passed](https://github.com/tya5/chrona/actions/runs/37201421690).

## Literal issue acceptance

### Issue #1114

- Source: [#1114](https://github.com/tya5/chrona/issues/1114)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | start-to-at, and start-to-start, with the target to the right; | met | [Neutral outward fixtures](https://github.com/tya5/chrona/blob/8420d007e5d0881bb3ac6e97f5a1cf9203e00f58/tests/unit/chrona/presentation/scene/test_relation_mark_safety.py) | — |
| 2 | the mirrored end-to-end case with the target to the left; | met | [Mirrored fixture](https://github.com/tya5/chrona/blob/8420d007e5d0881bb3ac6e97f5a1cf9203e00f58/tests/unit/chrona/presentation/scene/test_relation_mark_safety.py) | — |
| 3 | a bar with no free gap above, and one with no free gap below. | met | [Blocked-side fixtures](https://github.com/tya5/chrona/blob/8420d007e5d0881bb3ac6e97f5a1cf9203e00f58/tests/unit/chrona/presentation/scene/test_relation_mark_safety.py) | — |
| 4 | For each, no relation segment overlaps the interior of any bar by more than the stroke width, and the first segment leaves the port outward. | met | [Completed-path assertions](https://github.com/tya5/chrona/blob/8420d007e5d0881bb3ac6e97f5a1cf9203e00f58/tests/unit/chrona/presentation/scene/test_relation_mark_safety.py); 59 focused tests passed | — |
| 5 | A Scene check counts own- and foreign-bar crossings corpus-wide; it must be 0 after regeneration. | met | [64-pair audit](https://github.com/tya5/chrona/pull/1138): own 10→0, foreign 8→0 | — |
| 6 | Existing compliant routes are unchanged. | narrowed | [Owner withdrawal](https://github.com/tya5/chrona/issues/1114#issuecomment-5979291651); accepted changes disclosed in PR | [#1109](https://github.com/tya5/chrona/issues/1109) |
| 7 | On target B, `avionics-cdr` no longer crosses the Avionics bar. | met | [Actual Scene/SVG audit](https://github.com/tya5/chrona/pull/1138); already-correct main baseline unchanged | — |

## Programme-level criteria (optional)

Architecture: Layout owns completed geometry and mark-interior checks; terminal
authorization covers only the outward stub. Scene observes; adapters serialize.
No schema, View, Theme, budget or project-specific rules change. No quality
mitigation or examples workaround is included.

Merged as `53227a5b76da8542d432d2ae8ec0d58409a51be1`. Final snapshot
is byte-identical to the audited snapshot across all 64 Scene/SVG pairs.
Closed with main commit [8420d007e5d0881bb3ac6e97f5a1cf9203e00f58](https://github.com/tya5/chrona/commit/8420d007e5d0881bb3ac6e97f5a1cf9203e00f58), exact-SHA [derived-main/ready](https://github.com/tya5/chrona/actions/runs/37202949335), and [three-OS release gate](https://github.com/tya5/chrona/actions/runs/37203065647).
