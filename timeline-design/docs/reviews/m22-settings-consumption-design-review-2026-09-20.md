# M22 settings-consumption design review — 2026-09-20

**Disposition:** Pass — implementation may begin only after D24 publication

## Review result

The remediation has one owner for each decision. Theme owns decoration; Layout owns
placement and visibility; Detail owns wording and label requiredness; Scene owns
completed geometry, stack metadata, and conditional primitive presence; SVG owns only
serialization. Rect rounding is therefore added to Scene rather than recovered in the
adapter. Stable stack identity remains metadata on row-aligned and independent-lane
surfaces.

PR 13's single-sample exact inert set is rejected as a completion oracle because it
confuses an absent conditional family with an ignored field. The replacement matrix
requires a trigger and an owned-property observer for every conditional setting group.
It still detects both regressions: an observer that becomes equal fails, and a setting
that becomes live under a different owner fails its declared classification.

The design does not widen scheduling semantics, does not add an external panel, and
does not authorize M23. The D24 fixture and validator close the new Rect payload,
comparison metadata, conditional families, and v0.2 layout-authority rule before any
runtime edit.

## Implementation authorization

I24-1 through I24-4 may proceed in order after the design-only commit is published and
its GitHub tree is verified. A change to primitive families, ownership, diagnostics, or
schema version requires a new design publication first.

## D24 addendum review

The pre-I24-2 implementation review correctly stopped before code because the original
text named variance roles but did not close the unknown trigger or exact conditional
family placement. Specification 08 and the M22 plan now define both without changing
schema or semantic authority. I24-2 may resume only after this addendum is published
and its remote tree is verified.

The first I24-2 boundary test then exposed a right-edge case in the valid ASTER
fixture. The design now closes that case with a measured whole-label left shift at the
viewport margin, preserving text and temporal geometry. This is a placement refinement
inside the already owned conditional families, not adapter repair.

The I24-3 pre-review also stopped before code on two unspecified choices. The final
addendum now defines next-finer minor ticks and a total mapping from every schema label
source to Scene behavior, including duplicate precedence and optional omission. These
rules consume existing schema only and do not widen semantic authority.
