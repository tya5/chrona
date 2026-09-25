# Design Plan — #410 I410-2 Tabular Metrics v3

**Parent programme:** `issues-410-412-411-typography-orientation-system-font-design-plan-2026-09-25.md`.

## Purpose

Complete the next approved #410 slice without treating an OpenType feature as
adapter paint.  The design must make proportional and tabular numeric geometry
an identity-pinned, measurable Layout input and give signed-day table facts a
semantic treatment selection.

## Established facts

* The live context contract is `render-context/v0.15`, whose font descriptor
  permits only `declared-metrics-v2`.
* v2 records only default cmap advances.  It cannot prove the advances after a
  numeric OpenType feature substitution.
* Packaged Noto Sans has `pnum` mappings from its default tabular digits to
  unequal proportional glyphs; its `tnum` result is the default equal-width
  digit set.  Therefore measuring default advances as “proportional” would be
  false.
* `signedDays` is already a finite View format and its public HALCYON columns
  are right aligned, but normalized table content carries no typography role.

## Design questions

1. Define a v3 metrics payload that proves both selected digit advance sets and
   rejects incomplete/equal-width-invalid tabular data.
2. Decide the Context successor and atomic resource migration boundary.
3. Define how Layout selects a numeric treatment for a `signedDays` table cell
   without putting Theme syntax or font-feature policy into View or Scene.
4. Specify how SVG, Typst, and TikZ receive an already-selected numeric feature
   and how non-numeric text remains proportional.
5. Define fixture, importer, public evidence, and negative-test requirements.

## Required outputs

1. English design amendment with data model, ownership, migration, and explicit
   exclusions.
2. Architecture review against the Theme → Layout → Scene → adapter chain.
3. Independent implementation plan with atomic migration and acceptance gates.

No metrics, schema, Theme, View, or adapter implementation changes occur in
this planning phase.
