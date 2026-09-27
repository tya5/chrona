# Implementation Correction — #466 C3 Evidence after #467 Lanes

**Plan:** amends the #466 implementation plan and its amendment 2. **Base:** `812d5c77` (C2 landed as View v0.25).

## Finding

- **C3** declared HALCYON `02-programme-board`'s three Project notes with `candidates: [plot, nearest-free, tail]` and no rail slot.
- **Two placed.** `window-note` and `station-note` place cleanly.
- **One did not.** `tvac-note` exhausts the finite declared search (1024 positions), and its box and tail still collide with dependency routes, marks and variance labels. The anchor is the finish of `payload-tvac`, which lies before the as-of line. Row 3 of the acceptance forbids a box crossing that line, so the search is confined to the densest part of the plot. The #449 completion then occludes a variance label, and `tools/check_scene_perceptibility.py` rejects it.
- **The knobs don't help.** Changing `maxPositions` (4096), `maxInlineEm` (8, 12 or 18) or the anchor endpoint does not produce a clear box. This is a fixture-density limit, not an engine defect.

## Decision

- **No hidden change.** We do not widen a limit, drop an obstacle class, or narrow the acceptance. The review of the design forbids each of these.
- **Re-sequence C3 and C4.** They run after #467 L3, which moves `02-programme-board` to `rows.mode: lanes`. The 26 automatic rows then pack into at most 12 lanes, and the plot area the notes search changes entirely. Row 3's literal fixture is re-measured on that slide.
- **If `tvac-note` still cannot place,** a design correction is published before any code change.
- **Kept for C3:** the uncommitted View and Theme edits, preserved as a patch by the lead.

## Rows met by C2

These are verified again in the acceptance review:
- row 1 (one obstacle set, the note-beside-dependency test);
- row 2 (declared candidates, evidence unchanged apart from version provenance);
- row 5 (deterministic, bounded, decision records);
- row 6 (the Theme balloon; none renders as today).

Row 7 (the specification) is part of C4.

## Added to C4 (2026-09-27, from #465)

`annotation-note-box` and `annotation-note-text`, the candidate-mechanism roles, have no `ContrastClass` in `semantic_registry.py`. As a result, `tools/presentation_contrast.py` does not evaluate note text for any container kind. C4 classifies both roles and migrates the Themes that bind them.
