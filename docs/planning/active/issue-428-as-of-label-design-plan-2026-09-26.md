# Design Plan — As-of Label Content and Label Chips (#428)

**Public base:** `dd8e5b0d` on `main`. **Source of truth:** [Issue #428](https://github.com/tya5/chrona/issues/428), Specifications 06 (View), 39 (axis and observation clarity), 50 (label placement), 07 (Theme roles).

## Published baseline

- `layout/surface_composer.py` builds the as-of label as `f"{label} {as_of.isoformat()}"`, so a bare `Today` is unreachable, and the date is an unlocalized ISO string.
- The label is a proper `LabelRequest` with a candidate ladder. Nothing can place a background shape from a text placement's measured bounds.
- 12 shipped Views declare an `asOf` marker, whose rendered text today includes the ISO date.

## Literal acceptance ledger

1. “`as_of_label: Today` renders as `Today`, with no date appended.”
2. “A document that wants a date with the label states the form it wants, in the vocabulary axis labels already use.”
3. “A label can carry a background sized from its own measured text, and the mechanism is not specific to the as-of marker.”
4. “One committed example renders an as-of label as a bare word in a filled chip, and reproduces byte-identically.”

## Decisions

- The View syntax for the date form. This needs a View version, because the default meaning of `label` changes. The published #466/#467 designs name View v0.23 but have not landed; whichever lands first takes the next number.
- The chip mechanism: a Theme role keyed by label purpose; Layout geometry; its obstacle footprint; contrast ground.
- Corpus migration: keep the dates on existing slides through an explicit `date` form, and choose the one example.
- Out of scope: a declared candidate ladder (proposal item 4). It is not in the literal acceptance; it is recorded for #466's placement model.

## Slices

- **I428-1:** View v0.23 with the as-of `date` form, and migration of all Views.
- **I428-2:** the generic label chip plus the committed example.
- **I428-3:** acceptance review.
