# Axis Name Tables

**Status:** Normative for Issue #432. This specification supersedes the
locale-selected axis vocabulary described in [Slide-grade Review Vocabulary](45-slide-grade-review-vocabulary.md)
and the historical Scene-owned axis formatting language in
[Table-Timeline Presentation](24-table-timeline-presentation.md). It does not
change date or fiscal-calendar semantics.

## Contract

The View labels tier owns a finite form and MAY own `label.nameTable`, whose
value is the exact ID of a validated axis name table. The default is the
Render Context's exact declared locale ID. The selected table is independent
of that locale when explicitly named. The View schema admits only supported
finite IDs and only on labels tiers; changing this public grammar requires a
new View version. View v0.22 is the first version with this field; it replaces
v0.21 as runtime ingress, with no compatibility reader.

The engine bundles a versioned, validated name-table resource containing
`en-US` and `ja-JP`. Each table supplies complete month-name arrays and
closed templates for all supported axis label forms. Templates use only
validated semantic placeholders and cannot be authored inside a View.
Adding a third language requires a table-data entry and schema/catalog
registration, not an axis formatter branch. Arbitrary host locale lookup,
format strings and path-based table discovery are forbidden.

Layout uses the selected table to produce the same text for natural-bucket
candidate fitting and final placement. The selected ID is part of the typed
placement outcome. Scene projects completed text and adapters serialize it;
neither may format an axis date. A name table never changes interval dates,
fiscal-year selection, position or schedule facts.

## Equivalence and diagnostics

No two month forms may produce the same string under one table without a
declared, checked equivalence. The bundled-resource validator compares all
twelve months for the month-only and year-bearing form groups and rejects
undeclared collisions or false equivalences. A checked public audit records
the groups. When the author selects a noncanonical equivalent form, Layout
emits `W_LAYOUT_AXIS_FORM_EQUIVALENT` with table ID, selected form and canonical
form. A canonical selection remains valid without a runtime warning because
the audit already discloses its equivalent. An invalid table or unknown ID is
an error; no alternate table is silently chosen.

The `ja-JP` numeric forms mean `01` and `2026-01`; they no longer alias the
Japanese named forms. Japanese short and long named forms may be equivalent
when explicitly declared and audited. This intended source-visible behavior
change is included in the atomic View v0.22 corpus migration.
