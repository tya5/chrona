# Architecture Review — Axis Typography Admission (#478)

**Reviewed:** [axis-role amendment](../../design/issue-478-axis-typography-role-admission-amendment-2026-09-27.md),
[rebase correction](../../design/issue-478-role-admission-rebase-correction-2026-09-27.md),
Specification 39 §1.2, View v0.25 schema, #426 architecture/acceptance
reviews, `ThemeTokenView.text_treatment`, Layout axis-tier composition,
semantic registry and Scene projection.

**Decision:** accept one View-declared parameterized **measurement** family,
bounded to Layout text/axis metrics. This preserves a real public View
extension point without allowing an arbitrary paint/effect role. The separate
ordinal Scene paint roles stay finite. Direct and Scheme pointers remain
exact under the #478 validator; Scheme colour bindings to an otherwise
measurement-only custom role must fail. No #426 visual behavior is changed.

The old Specification 39 sentence claiming that `typographyRole` itself
paints a label was inconsistent with the later explicit ordinal semantic-id
rule and implementation. The correction resolves that ambiguity for Theme
admission. Structural tests must show a custom axis measurement role loads
only with permitted properties, while its invalid paint binding fails, and
that `axis-label2`/`axis-label3` continue to own their completed paint.
