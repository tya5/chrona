# Reusable annotation policy (#1343)

Current behavior, identity, precedence, diagnostics and ownership are defined
once in [Spec44](../specification/44-usable-explicit-rows-and-annotation-rail.md#reusable-project-note-placement-1343).
[Design plan](../planning/active/issue-1343-annotation-policy-design-plan-2026-10-12.md).
The finite binding list, rather than a selector DSL or project-ID table,
preserves the existing designs' distinct point/span ordering and anchor facets.
Existing explicit declarations remain untouched; only opted-in resources gain
automatic expansion. Schemas add optional members in place under Spec56;
candidate/anchor vocabulary must be shared, not copied. No examples migration
is developer-owned. Rendered five-design acceptance remains unverified.
