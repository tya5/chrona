# Architecture Review — Footer Side-Content Geometry Closure (#455)

**Design under review:**
`issue-455-footer-side-content-geometry-design-2026-09-26.md`.
**Decision:** Accepted for implementation planning.

## Whole-architecture review

| Concern | Result | Required guardrail |
| --- | --- | --- |
| Layout responsibility | Pass | Measured cursor advancement, swatch reservation, final child-slot extents, warning completion, and successor flow are all physical Layout facts. |
| #445 scope | Pass | Paragraph wrapping/stacking stays in the group-detail/milestone helper; #455 only coordinates finite footer-slot completion and independently composes notes/legend. |
| #449 fit policy | Pass | Explicit visible overflow remains visible, warned, and canvas-complete.  Ellipsis is used only where the slot explicitly declares it. |
| Scene/adapters | Pass | They receive no new policy request, measurement input, or clip instruction.  Existing primitive/slot/warning projection is sufficient. |
| #446 boundary | Pass | The future evaluator observes final containment; no current defect becomes a host relation, allowlist entry, or evaluator-side repair. |
| Footer flow | Pass | The #445 annotations successor receives the final union extent, preventing a narrow source-specific correction from becoming stale as other footer children complete. |

## Required implementation structure

1. Extract a private footer-band coordinator from the current inline
   #445 downstream-translation block.  Its inputs and outputs must be typed
   `SlotPlacement` collections/replacements; it must not inspect Scene
   primitives or View syntax.
2. Keep notes and legend composition helpers separate by semantic family.
   They may share a measured-slot result value, but not a branchy generic text
   loop that would obscure the distinct swatch and source-order rules.
3. Use completed `TextPlacement.bounds.block_size` for notes advancement.
   Do not substitute a font-size constant, a renderer line-height, or a Scene
   tolerance for physical sequencing.
4. Ensure the legend's reserved leading interval is passed to both ellipsis
   measurement and final placement.  A post-hoc containment assertion alone
   is insufficient because it would reject valid source input rather than
   complete its declared disposition.

## Review conclusion

The design resolves the newly discovered P0 failures structurally without
generalizing #445 into a Scene collision system.  It aligns with the existing
placement closure, visible-fit policy, and downstream footer allocation.  A
published implementation plan is required before source changes resume.
