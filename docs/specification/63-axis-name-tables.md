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

`column.finishDeltaPlan` and `column.finishDeltaBaseline` name the reference
selected by the built-in `column.finishDelta` header under Spec06's forecast
comparison rule (#1810). The locale table supplies both; authored literal
headers and explicit wording overrides keep their existing precedence.

(#1724) The engine also bundles `wording-tables-v0.1.yaml` (schema `wording-tables-v0.1.schema.yaml`), a sibling
of the axis resource: one complete table per supported locale (`en-US`, `ja-JP`) mapping the same closed wording
keys to text. A locale lacking any key, an unknown key, an empty text or a third table is `E_WORDING_TABLE_RESOURCE`.
The keys are `column.task`, `column.plan`, `column.lane`, `column.items`, `marker.today`, `marker.asOf`, `marker.baselineNew` (`new`), `marker.baselineRemoved` (`removed`, `ja-JP` `削除`; the ghost title reads `<title> (<removed>)`),
`legend.planned`, `legend.actual`, `legend.milestone`, `legend.dependency`, `legend.asOf`, `legend.calendar-closed`,
`legend.critical-edge`, `legend.forecast`, `legend.progressFill`, `legend.actual-ahead`, `legend.actual-on-track`, `legend.actual-behind`, `legend.snapshot`, `legend.deadlineMark`,
`missing.unknown` and `missing.inProgress`; and the keys for words presets used to write as literals: `legend.planned-plain` (`Planned`, distinct from the `Task duration` of `legend.planned`), `legend.baseline`, `legend.current-plan`, `legend.gate`, `legend.holiday`, `column.owner`, `column.number` (`No.`), `column.phase`, `column.finishDelta` (`Δ finish`) and `summary.days` (the Titlecard `DAYS`); and the keys for design-voice words (#1724 P4d): `legend.plan`, `legend.missing-actual` (`Not yet observed`), `legend.missing-actual-in-progress`, `legend.in-the-wings`, `legend.calendar-exception`, `legend.period`, `legend.depends-on`, `legend.other` (the folded colour-scale entry that code names) and `column.no` (`No`, with no full stop; `column.number` stays `No.`, because a `wording.keys` override is not locale-scoped and so cannot turn `No.` into `No` for English alone). and the day-unit keys (#1790) `delta.unit.calendarDay` (`d` / `日`) and `delta.unit.workingDay` (`d` / `営業日`), which the View's `comparison.deltaUnit` selects for the unit after every signed finish delta (table cell, bar label, Summary metric); `wording.keys` overrides them like any key. The `ja-JP` `quarter-year` form is `2026年Q4` (year first, as the locale writes it; the same text as `year-quarter`), while `en-US` stays `Q4 2026`. A Summary Profile metric `label` accepts a literal or a `{wording: <key>}` reference, as `summary.days` does for the Titlecard. `markerPresentation.label` and a lane table column `header` accept a literal or a `{wording: <key>}` reference like the other places.
The Layout-defaulted labels with no Detail entry are table keys too: the Progress key when the Detail Profile declares none (`legend.progressFill`), the Actual variance qualifiers `Ahead`, `On track`, `Behind` (`legend.actual-ahead`, `legend.actual-on-track`, `legend.actual-behind`; `前倒し` / `予定どおり` / `遅れ` in `ja-JP`) and the default lane-table headers (`column.task` or `column.lane`, and `column.items`). `wording.legend`, `wording.keys` and an authored Detail label override them as §9.3 orders. Under `--locale ja-JP` no English built-in wording remains in a scene except authored content (titles, a preset's own literal labels, proper names). The Render Context locale selects the table (an unsupported locale reads `en-US`); `nameTable` on an axis tier is
unchanged and does not select wording. A View, Layout or Detail Profile references an entry as `{wording: <key>}`
(`urn:chrona:common-v0.1#/$defs/wordingRef`); resolution and the override precedence are specified in
[View Model §9.3](06-view-model.md). Adding a locale is a table entry in the resource and schema; a test lists the
keys and fails when a locale lacks one. Case is never part of the table: every `en-US` value is sentence case (`Today`, `Non-working day`, `As of`), and a design that wants `as of`, `actual` or `non-working day` in lower case, or `TODAY` in capitals, sets the existing Theme typography `textTransform` (`lowercase`, `uppercase`) on the role that draws the text (`as-of-label`, the legend role). Japanese text has no case and is unchanged by a transform. A design therefore needs no key of its own for a case variant. The `en-US` entries equal the English literals the built-in presets carried before the
table, so a preset that keeps its literals renders byte-identically.
