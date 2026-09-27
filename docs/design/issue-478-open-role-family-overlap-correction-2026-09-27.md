# Design Correction — Open Role Family Overlap (#478)

**Amends:** the [axis typography amendment](issue-478-axis-typography-role-admission-amendment-2026-09-27.md)
and [legend paint amendment](issue-478-legend-role-admission-amendment-2026-09-27.md).
**Trigger:** the I478-3 consumer inventory found that the two legitimate
open-name producer families overlap when no View or Detail Profile is selected.

An arbitrary non-empty role name can be named by a View axis tier as a
measurement role and can also be named by a Detail Profile legend entry as
a fixed-square paint role. Theme closure is intentionally independent of
both resources. It therefore cannot determine the author's intended use
from the name alone. For an otherwise unregistered name, admission is the
**union of the two bounded potential consumer sets**: the axis-tier text
measurement properties and the legend fallback Rect paint properties. A
property from neither set remains unsupported. This union is not a claim
that axis labels paint from the role: they still use their ordinal visual
roles. Nor does a paint declaration supply missing measurement tokens when
the View selects that name as `typographyRole`.

Known roles remain governed by their explicit, narrower consumer contract.
The open-name union does not legalize `variance-behind.strokeWidth`,
`annotation.strokeWidth`, or a paint effect on a known Text/Icon role.
`axisMonth` and `axisQuarter` are known measurement roles; a Scheme `fill`
target on either remains unsupported. A previously unknown `fiscalAxis.fill`
target is admissible as potential legend paint even when a View also happens
to use `fiscalAxis` for measurement; load-time admission cannot reject it
without breaking #427. A context-aware unused-role or intent lint is a
separate future feature, not #478's Theme capability gate.

The I478-3 tests must assert these distinctions. In particular, replace
the earlier expectation that **every** custom axis role's Scheme paint
target fails: only paint targets on known measurement-only roles fail at
load. A novel role's paint target is accepted as legend-capable, while
Scene axis-label paint remains tied to its ordinal role. No schema, output,
diagnostic identifier, or migration boundary changes.
