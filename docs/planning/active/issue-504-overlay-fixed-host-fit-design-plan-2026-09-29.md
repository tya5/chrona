# Design-plan correction — overlay fixed-host fit (#504)

Published baseline: `origin/main` `3475e401`; [R2 implementation plan](issue-504-fill-only-label-search-implementation-amendment-2026-09-29.md) and [Specification 33 §13.1](../../specification/33-intent-oriented-layout.md) govern the open slice. [PR #548](https://github.com/tya5/chrona/pull/548) is not merged. Its CI shows `11-overlay-briefing` rows ending at block 1228 while the fixed timeline host ends at 1185; macOS and Windows each fail the same containment test. The public Scene has a typed `W_LAYOUT_ROW_DENSITY` shortage of 43. Ubuntu's result is pending. This is new R2 evidence, not accepted release evidence.

The literal #504 acceptance criteria remain unchanged (the attached-point host is included by the issue comment):

1. The bundled default and the `chrona init` starter keep an informative table under lanes. Where a lane holds one item, the lane label is that item's name. Otherwise the default View does not use lanes. Either way, no table column is empty on every row. The #498 gate is extended to assert this.
2. Lane height can grow into available plot height for stagger rows before a name is suppressed, as a declared Layout policy, for example with `rowDistribution: fill` (#434). A name is suppressed only when the lane cannot grow. On 02, the suppression count is reported in the acceptance review, and every suppressed name is attributed to a lane that could not grow.
3. The lane table does not repeat the group header's text on the group's first lane, and it never shows an empty label next to a count.
4. A mechanical check over committed lane slides: the ratio of shown to packed names is reported in the corpus coverage, so a regression is visible.

Decide whether the wallboard overlay's fixed Theme-owned review extent should be increased to contain its now-measured fill rows, or whether the profile should become content-sized. Review the fixed-height intent of #382, available viewport, other token consumers, fit-completion rules, row/annotation geometry, and generated artifacts. Do not clamp Layout rows or silently change #504's measured-label minimum. Record migration and a whole-architecture review before code.

The next independently publishable slice is a resource fit correction: adjust only the approved profile/Theme owner if feasible; verify the 11 containment test, focused geometry/perceptibility tests, all public materializers and intended Scene/SVG diffs, then run the CI release gate. Publish design/review, implementation amendment, and resource/evidence separately. Keep #504 open until the R2 implementation and acceptance review pass on main.
