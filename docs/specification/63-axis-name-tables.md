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
validated semantic placeholders, including ISO week-year and ISO week number,
and cannot be authored inside a View. Table validation computes every
month-form pair for all twelve months and rejects an undeclared, false or
imprecisely scoped coincidence. A legitimate month-specific coincidence,
such as English `May`, is declared with its exact month numbers.
Adding a third language requires a table-data entry and schema/catalog
registration, not an axis formatter branch. Arbitrary host locale lookup,
format strings and path-based table discovery are forbidden.

A week labels tier selects `iso-week` (the default, `2026-W42`) or a form that names the week's first day:
`start-day-month` (`12 Oct`; `10月12日` under `ja-JP`) and `start-numeric` (`10/12`; `10/12` under `ja-JP`). The first day is the
start of the natural week interval the tier already computes, so a week that crosses a month or year boundary is named by
its own first day, not by the clipped window edge; there is no week-start setting. `secondary` accepts the same forms
(#1278).

Layout uses the selected table to produce the same text for natural-bucket
candidate fitting and final placement. The selected ID is part of the typed
placement outcome. Scene projects completed text and adapters serialize it;
neither may format an axis date. A name table never changes interval dates,
fiscal-year selection, position or schedule facts.

## Equivalence and diagnostics

No two month forms may produce the same string under one table without a
declared, checked coincidence. The bundled-resource validator compares all
twelve months for every month-form pair and requires exact month-scoped
records for all collisions. A checked public audit records them. When the
author selects a noncanonical form on a coincident month, Layout emits
`W_LAYOUT_AXIS_FORM_EQUIVALENT` with table ID, selected form, canonical form
and month number. A canonical selection remains valid without a runtime
warning because the audit already discloses its equivalent. An invalid table or unknown ID is
an error; no alternate table is silently chosen.

The `ja-JP` numeric forms mean `01` and `2026-01`; they no longer alias the
Japanese named forms. Japanese short and long named forms may be equivalent
when explicitly declared and audited. This intended source-visible behavior
change is included in the atomic View v0.22 corpus migration.

## Built-in wording tables

(#1724) The engine also bundles `wording-tables-v0.1.yaml` (schema `wording-tables-v0.1.schema.yaml`), a sibling
of the axis resource: one complete table per supported locale (`en-US`, `ja-JP`) mapping the same closed wording
keys to text. A locale lacking any key, an unknown key, an empty text or a third table is `E_WORDING_TABLE_RESOURCE`.
The keys are `column.task`, `column.plan`, `column.lane`, `column.items`, `marker.today`, `marker.asOf`,
`legend.planned`, `legend.actual`, `legend.milestone`, `legend.dependency`, `legend.asOf`, `legend.calendar-closed`,
`legend.critical-edge`, `legend.forecast`, `legend.progressFill`, `legend.actual-ahead`, `legend.actual-on-track`, `legend.actual-behind`, `legend.snapshot`, `legend.deadlineMark`,
`missing.unknown` and `missing.inProgress`.
The Layout-defaulted labels with no Detail entry are table keys too: the Progress key when the Detail Profile declares none (`legend.progressFill`), the Actual variance qualifiers `Ahead`, `On track`, `Behind` (`legend.actual-ahead`, `legend.actual-on-track`, `legend.actual-behind`; `前倒し` / `予定どおり` / `遅れ` in `ja-JP`) and the default lane-table headers (`column.task` or `column.lane`, and `column.items`). `wording.legend`, `wording.keys` and an authored Detail label override them as §9.3 orders. Under `--locale ja-JP` no English built-in wording remains in a scene except authored content (titles, a preset's own literal labels, proper names). The Render Context locale selects the table (an unsupported locale reads `en-US`); `nameTable` on an axis tier is
unchanged and does not select wording. A View, Layout or Detail Profile references an entry as `{wording: <key>}`
(`urn:chrona:common-v0.1#/$defs/wordingRef`); resolution and the override precedence are specified in
[View Model §9.3](06-view-model.md). Adding a locale is a table entry in the resource and schema; a test lists the
keys and fails when a locale lacks one. Upper-casing of a label such as `TODAY` remains a Theme typography transform
and is not part of the table. The `en-US` entries equal the English literals the built-in presets carried before the
table, so a preset that keeps its literals renders byte-identically.
