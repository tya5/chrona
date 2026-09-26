# Design Correction — As-of Label Chips (#428)

**Corrects:** [#428 design](issue-428-as-of-label-design-2026-09-26.md), Contract 2 and the example. **Found while implementing** I428-2. Contract 1 (View v0.23, the `date` form) is unchanged.

## 1. Chip semantics are registered, not derived from strings

The design named the chip role `<label purpose>-chip`, derived at run time. Two repository invariants reject that:
- every emitted purpose must be a registered semantic (`test_every_emitted_purpose_is_a_registered_semantic`);
- every registry entry must have a production lookup path (`check_semantic_registry_reachability`).

**Corrected contract:** the semantic registry declares one chip binding per label semantic that may carry one:
- `asOfLabelChip` → role `as-of-label-chip`;
- `memberLabelChip` → `member-label-chip`;
- `finishDeltaChip` → `finish-delta-chip`.

All three have purpose `label-chip`. `label_chip_semantic(label_semantic_id)` in the registry is the single mapping Layout uses. The mechanism stays generic: no Layout branch names a purpose, and any label semantic added to the mapping gains chips.

Chips carry no contrast class. The label text's ground is found by the existing composited-ground analysis. The chip is a Rect under the text, so text-on-chip contrast is gated as for any painted surface.

## 2. The as-of anchor grows with a chip

Side candidates centre a label on its anchor. The as-of anchor is `body size` tall at the top of the timeline. A chipped label is taller by twice its block padding, so a side candidate starts above the timeline, is rejected by the slot bounds, and falls back to `above`, over the axis labels. This was observed on HALCYON `04` as `E_SCENE_TEXT_INTERSECTION`.

**Corrected:** when an `as-of-label-chip` is declared, the as-of anchor is the chipped label's full block extent (`line block + chip padding`), so its top is the timeline top. Without a chip the anchor is unchanged, so slides without chips stay byte-identical.

## 3. The example is the wallboard family, not a derived Theme

A derived v0.12 Theme cannot be a committed slide's Theme: `presentation_coverage` requires every slide resource at the live Theme version, and the gallery pairs `02` with other wallboard slides.

**Corrected:** the `wallboard` Theme declares `as-of-label-chip`. All four wallboard slides draw the as-of label in a chip:
- `02-programme-board` declares `label: Today` with no date, which is the literal example;
- `04`, `07` and `11` keep a dated label (`as of Aug 20, 2027`) in the same chip.

## Review

This correction changes no ownership. Layout still owns geometry and footprint, the registry owns semantics, Scene projects a Rect, and the adapters are unchanged. Byte impact:
- the four wallboard slides gain a chip;
- every slide with an as-of label changes text (the localized date, Contract 1);
- no other geometry changes.
