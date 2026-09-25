# Axis and Visible-Failure Design (#405, #406, #407, #408, #400)

**Status:** Proposed design.

## Decision

Replace the positional axis array and dead `ticks` field with independently
typed axis tiers. Replace the strict/permissive failure split with a published
visibility classification. Both are Layout contracts: View declares intent,
Layout measures/selects/records outcomes, Scene projects completed values, and
adapters never infer a fallback.

## Axis tiers

View v0.16 has an ordered `axis.tiers` array. Each tier declares exactly one
unit (`day|week|month|quarter|half|year`), a unit-valid label form, a positive
`every`, alignment, and one role: `band`, `labels`, `grid-major`,
`grid-minor`, or a permitted combination specified by the schema. There is no
array-position meaning and no separate `ticks` field.

The label-bearing tier may instead use `unit: auto`; Layout tries the finite
ordered candidates day through year with that tier's label forms and selects
the densest complete fit. `every` reaches `axis_intervals(..., tick_step=...)`.
Every declared tier must produce a band, grid, label, or a recorded suppression;
an unused tier rejects during View normalization.

Label forms are enums per unit, not one global enum. Locale selects only a
finite declared name table (`en-US` or `ja-JP`) and does not restrict the
selected form. Thus an English abbreviated month can be used under ja-JP and
a Japanese name form under en-US. Arbitrary format strings are excluded.

Half/year/quarter bucket starts derive from the Project Calendar's declared
fiscal-start month. Calendar data owns that offset; View does not. ISO week
numbering remains the only week form in this release. Project-relative weeks
are deliberately absent until a semantic origin and snapshot rule are designed.

## Failure classification

Every Layout failure is classified in a finite registry as either:

* **invisible loss:** a reader cannot determine that information was omitted or
  incorrectly substituted. It must diagnose or emit an explicit recorded,
  visible substitute according to declared overflow;
* **visible degradation:** the delivered surface exposes the defect directly.
  It follows the relevant slot/path policy, records a warning, and may render.

Axis-label non-fit is invisible loss. Its tier declares `overflow:
diagnose|thin-with-record`; the latter deterministically retains every Nth
candidate, records every omitted identifier in `SurfacePlacement`, and emits a
visible axis-density warning. Silent omission is removed.

Row required extent is visible degradation. P1 computes it; the draft path may
grow under the existing `WIDTHxauto` contract or render a policy-authorized
cramped surface with `W_LAYOUT_ROW_DENSITY`. Immutable materialization follows
the bound slot policy and diagnoses when its reader cannot observe the source.
No helper may override a declared slot policy with an unconditional raise.

Relation routing and table ellipsizing retain their existing classifications;
the registry records rather than silently redefines them.

## Invariants and migration

Layout records selected tier, candidate intervals, label outcomes, and the
failure-classification decision in the placement closure. Scene has no
formatter, tick calculation, or warning policy. All Views/Contexts migrate to
v0.16 atomically; v0.15 is not read. Corpus evidence includes auto, every-N,
three tiers, fiscal April, half-year, both locale name tables, thinning record,
and both draft/immutable row-density outcomes.

## Non-goals

This design does not add rotated labels (P4), host locale discovery, arbitrary
date format syntax, project-relative weeks, or adapter-specific overflow.
