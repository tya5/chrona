# Design Amendment — View-Named Axis Typography Roles (#478)

**Amends:** [role-admission rebase](issue-478-role-admission-rebase-correction-2026-09-27.md).
**Finding:** the #426 View grammar permits any non-empty `typographyRole` on
an axis band or labels tier. A strictly enumerated Theme role list would
reject a valid newly named measurement role before any View is selected.
The #478 validator has no selected View by design.

The finite admission projection therefore has one additional **explicit
producer family**: a View axis tier may name a Theme typography role. Any
non-empty role name is potentially produced by that field, but this family
admits only the Layout-consumed text-treatment properties
(`fontFamily`, `fontWeight`, `fontSize`, `lineHeight`, `letterSpacing`,
`textTransform`, `numericSpacing`) and the axis-tier Layout metrics
`laneBlockSize` and `labelInset` where their consuming tier kind applies.
The other existing text/icon metrics may be admitted only if the same
axis-label placement path actually consumes them. This is **not** a general
escape hatch: arbitrary role names gain no Scene `fill`, `stroke`, shadow,
gradient, mark geometry, annotation container or policy properties from
the axis typography producer. Unknown names with those properties still fail
at load time. When the View actually selects a named role, Layout's existing
required-token checks diagnose an incomplete treatment; load-time admission
does not falsely claim that every valid potential role is selected today.

#426's current Scene projection paints the second/third labels tiers through
their closed `axis-label2`/`axis-label3` visual roles, while
`typographyRole` supplies measured text and lane geometry. A Theme may bind
distinct colours to those ordinal paint roles; it cannot bind a colour to an
arbitrary measurement-only `typographyRole` and expect Scene to use it. The
prior Specification 39 wording conflated these two roles. Correcting the
wording changes no rendered bytes, View syntax, Theme schema, or adapter
behavior. A future design may unify their identity, but I478-3 must validate
the published behavior, not silently implement a #426 paint migration.
