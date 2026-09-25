# Design Correction — #410 I410-2 Numeric Capability and Glyph Substitutes

**Corrects:** `issue-410-tabular-metrics-v3-design-2026-09-25.md`.

## Finding

The packaged draft-only Noto Color Emoji substitute face has no ASCII digit
glyphs.  Requiring every descriptor asset to publish proportional and tabular
digit maps would either make a valid character-level substitute unusable or
force fabricated numeric advances.  Neither preserves the measured-font
contract.

## Correction

`numericAdvances` is required for a face that can be selected as the primary
Theme face, but it is optional for a character-level substitute face.  A v3
resolver exposes this as a face capability:

* a primary face selected for a text treatment must have complete proportional
  and uniform tabular digit maps before Layout accepts `numericSpacing`;
* a substitute face may omit the maps and may supply only its declared missing
  glyph advances;
* `FontMetrics.width()` consults numeric maps only for ASCII digits.  If a
  selected primary face lacks the requested numeric capability, it diagnoses;
  it never borrows values from a substitute;
* substitute glyphs continue to be observable warnings and never confer
  numeric-feature support.

This keeps the feature guarantee attached to the actual selected face while
preserving the existing draft-only fallback boundary.  It does not relax the
I410-2 requirement for Noto Sans or any other Theme-selectable face.
