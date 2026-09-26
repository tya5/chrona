# Design — As-of Label Content and Label Chips (#428)

**Status:** proposed for whole-architecture review. **Plan:** [design plan](../planning/active/issue-428-as-of-label-design-plan-2026-09-26.md).

## Contract 1: the label is the label (View v0.23)

- `timePresentation`/`markers[]` keep their shape. An `asOf` marker gains an optional `date` object, `{form: localized-date, nameTable?}`. It uses the axis `localized-date` form and its name tables, and no new date vocabulary.
- **Meaning:**
  - without `date`, the rendered label is exactly `label`;
  - with `date`, it is `label + " " + formatted date`, where the date is formatted by the same function axis labels use for `localized-date` (Render Context locale, or `nameTable`).
- **View v0.23** is the next View version, because the default meaning of an existing field changes.
  - The loader accepts v0.23 only, as the repository keeps one current View version.
  - Every shipped View migrates.
  - The published #466/#467 designs, which named v0.23 for lane rows, will take the next number when they land. This is recorded on #467.
- **Migration:** every shipped View with an `asOf` marker gains `date: {form: localized-date}`, so its slide still shows a date, now localized rather than ISO. This is an intended text change, for example `As of 2026-05-20` → `As of 20 May 2026`. The one exception is the chip example (Contract 2), which declares no date.

## Contract 2: label chips (Theme, generic)

- A Theme may declare a role named `<label purpose>-chip` (for example `as-of-label-chip`, and equally `member-label-chip` or `group-header-chip`) with:
  - `backgroundTreatment: fill`;
  - `chipPadding`: a number token, as a ratio of the label's font size, used inline; half of it is used on the block axis;
  - optionally `markCornerRadius`: a ratio of the chip's block size;
  - a `fill` colour binding.
- **Layout.** When a label request's purpose has such a role:
  - the request's footprint is inflated by the padding before candidate search, so collision negotiation includes the chip;
  - after placement, Layout emits `ShapePlacement("chip:<placement id>")`, a Rect of the text bounds plus padding with the completed radius, at a paint order just below the text.
  - The same code path serves any purpose; no branch names the as-of marker.
- **Scene / contrast.** The chip is a normal Rect primitive with the chip role's paint. The existing composited-contrast analysis finds it as the label's ground, so text-on-chip contrast is gated like any painted surface.
- **Example:** the HALCYON `wallboard` Theme gains `as-of-label-chip` (a filled, rounded chip). `02-programme-board` declares its as-of marker as `label: Today` with no date.

## Tests

- A bare label, and a label plus date in en-US and ja-JP.
- The chip bounds equal the text bounds plus padding, and the chip paints under its text.
- The chip footprint participates in collision.
- A purpose with no chip role draws no chip.
- A second purpose, the member label, can take a chip through the same role naming (unit level).
- The committed `02-programme-board` shows `Today` in a chip; the other slides show localized dates.
