# Implementation Plan — As-of Label Content and Label Chips (#428)

## I428-1: View v0.23, as-of date form, migration

- **Files:**
  - `schemas/view-v0.23.schema.yaml` (copied from v0.22; `markers[].date`), the schema inventory and the resource mapping;
  - all shipped Views (version, plus `date` on as-of markers);
  - `review/v05_content.py` (label plus the optional date form into surface content);
  - `layout/surface_composer.py` (no concatenation; the formatted date comes from the axis formatter);
  - tests and fixtures pinned to v0.22.
- **Evidence:** as-of label text on the slides with an as-of line.

## I428-2: label chips and the committed example

- **Files:**
  - `layout/labels.py` / `surface_composer.py` (padding footprint, chip ShapePlacement);
  - `scene/v05_builder.py` (the chip primitive);
  - `model/theme_tokens.py` (the chip role reader);
  - the Theme v0.11 schema (`chipPadding`);
  - the HALCYON `wallboard` Theme and the `02-programme-board` View;
  - tests.
- **Evidence:** `02-programme-board` shows the chip.

## I428-3: acceptance review
