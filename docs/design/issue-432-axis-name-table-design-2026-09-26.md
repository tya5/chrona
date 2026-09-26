# Design — Independent Axis Name Tables (#432)

**Plan:** [design plan](../planning/active/issue-432-axis-name-table-design-plan-2026-09-26.md).
**Published base:** `055ad47f44e02653c1a2c3ec6af6550cfdf2c5e0`.
**Normative authority:** [Axis Name Tables](../specification/63-axis-name-tables.md).

## Decision and use cases

A bilingual review may use a Japanese document locale with an English axis,
or the reverse. The View labels tier therefore has optional `label.nameTable`,
a finite table ID independent of Render Context `locale`. The selected table
governs **both** automatic candidate measurement and final placed text. If
omitted, its exact ID defaults to the Context locale (`en-US` or `ja-JP`);
this is an explicit fallback lookup at the normalization boundary, not a
language-code branch in the formatter. Unknown IDs diagnose at View closure.

The table is a versioned, wheel-owned resource, initially `en-US` and `ja-JP`
entries in `axis-name-tables-v0.1.yaml`. It is validated as a whole at load.
Each entry supplies twelve short and long month names and closed templates for
the finite forms: `year`, `half-year`, `quarter`, `year-quarter`,
`quarter-year`, six month forms, `iso-week`, and `localized-date`.
Templates are resource data, not View-authored format strings. Allowed
placeholders are the closed semantic components `year`, `fiscalYear`,
`half`, `quarter`, `monthShort`, `monthLong`, `monthNumber`,
`monthNumeric`, `day`, `dayNumeric`, and `isoWeek`; the table validator rejects
unknown placeholders, missing forms, malformed month lists and empty output.
This keeps third-language additions data-driven without opening arbitrary
author code or syntax.

The `en-US` entry retains current English outputs. The `ja-JP` entry retains
the common `short-month` and `short-month-year` displays (`1月`,
`2026年1月`) but gives `numeric-month` a genuinely numeric `01` and
`numeric-year-month` `2026-01`. Japanese short/long name forms may still be
linguistically identical. The resource must declare such equivalence groups,
with a canonical form. Its validator checks all twelve months and a fixed
representative year for collisions, verifies the declared groups cover every
collision and no non-collision, and emits a checked table audit. Selection of
a noncanonical equivalent form records one
`W_LAYOUT_AXIS_FORM_EQUIVALENT` with table ID, selected form and canonical
form in the Layout diagnostic stream. The canonical form does not warn, but
the published audit reports the pair. Thus no distinct forms silently
collapse. A newly added table with undeclared collisions is invalid.

## Schema, identity and layer connection

The current live View v0.21 schema is immutable. View v0.22 adds optional
`nameTable: en-US|ja-JP` to every labels-tier `label` branch, including
`unit: auto`, and removes v0.21 from runtime ingress. Non-label tiers cannot
declare it. The table ID is syntax-checked by the View schema and resolved
against the validated built-in catalog during normalization. The selected ID
is carried by typed `AxisLabelIntent` and recorded on `AxisTierOutcome`;
Layout's axis formatter accepts a selected table value, never a locale.
`SurfaceLayoutRequest.locale` is removed if its only remaining use is axis
formatting; other locale-sensitive table-cell normalization retains its
existing Context input. This avoids propagating an unrelated environment
parameter into Layout geometry.

The authority chain is Render Context locale (default only) + View table/form
intent + bundled catalog → normalized `SurfaceContentInput` → Layout
intervals, text measurement, diagnostics and completed placements → Scene
projection → adapters. Scene and adapters receive final text; neither loads
tables, chooses a form, branches on locale or repeats measurement. Calendar
and fiscal bucket computation remain Project-owned and unchanged. The table
changes labels, never dates, interval identity or scale geometry.

The resource is engine-owned rather than a new mutable Render Context edge.
Its bytes ship with the wheel and are covered by package tests and the engine
identity of a materialization. An author-supplied table is a future resource
kind requiring an explicit immutable closure edge, schema and security review;
this issue does not infer one from a local path.

## Failure behavior and migration

- Unknown table ID: View-schema or closure diagnostic before Layout.
- Invalid bundled table, missing template, unknown placeholder or undeclared
  equivalence: deterministic resource diagnostic; no fallback to process
  locale or a different table.
- A valid alias form: visible Layout warning and checked table-audit entry;
  the rendered label is still the selected form's value.
- Automatic tiers use one selected table for every candidate and the final
  result. A collision warning is attached only to the selected form, not to
  unselected candidates.
- All source and wheel-mirrored View v0.21 resources, Context content pins,
  tests and the 21 public Scene/SVG materializers migrate atomically to
  v0.22. The Japanese numeric-month form intentionally changes; there is no
  legacy interpretation switch. Public materializers must remain
  reproducible after the atomic migration.

## Alternatives rejected

- A locale branch in `axis.py` or a View-only language override would leave
  vocabulary coupled to environment and cannot expose a third table as data.
- User-authored `strftime` or ICU patterns would open an unbounded language
  in a closed, inspectable View vocabulary.
- Treating `short-month` and `long-month` as silently equivalent under
  Japanese would repeat #408's failure. Inventing traditional month names
  solely to avoid a diagnostic would impose a cultural style not requested
  by the author.
- Creating a new Render Context resource edge for two fixed tables would
  multiply closures and pins without enabling user extension in this slice.

## Acceptance design

Tests must show `Jan`, `January`, `1月` and `01` under `ja-JP` by selected
table/form and `1月` under `en-US`; validate one explicit form collision and
reject one undeclared collision. A structural test rejects language-code
branching in the axis label path. Corpus tests compare public bytes after
v0.22 migration; the generated audit enumerates every equivalence and every
table. The [architecture review](../reviews/current/issue-432-axis-name-table-architecture-review-2026-09-26.md)
records the adjacent-contract check before implementation.
