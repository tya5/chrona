# Issue 254 Advanced-Contract Example Theme-role Implementation Amendment

**Amends:**
`docs/planning/active/issue-254-advanced-contract-example-implementation-plan-2026-09-22.md`

**Existing design authority:**
`docs/reviews/current/issue-133-view-contract-design-correction-2026-09-22.md`

The E254-1 materialization must add the already-required
`dependency-critical.stroke` mapping to the selected HALCYON `briefing` Theme.
The initial implementation uncovered its absence when the first public
table-timeline View selected a critical relation: the renderer correctly
rejected the missing resolved Theme role with `E_THEME_ROLE_REQUIRED`.

This is not a new semantic, Theme contract, or renderer policy. The closed
registry and #133 design already name `dependency-critical` as the required
Theme role for a critical relation View. The amended slice adds the missing
authored mapping alongside the new View/context, asserts that critical paths
serialize with that role, and verifies existing generated SVGs remain
byte-identical because none currently selects it.
