<!-- chrona:literal-acceptance/v1 -->

# Issue #1013: translucent-ground contrast, acceptance review

Source: [Issue #1013](https://github.com/tya5/chrona/issues/1013), re-fetched 2026-10-03 after the code merge (body unchanged since filing; no acceptance table; the three comments are this work's claim with owner-level decisions J1 to J5, a status block and a state line; no new rows). The rows below are the literal asks of the body's Direction and the assignment constraints. Work record: [issue-1013-translucent-ground-2026-10-03.md](../planning/active/issue-1013-translucent-ground-2026-10-03.md); living contract [Specification 46](../../specification/46-completed-scene-paint.md) section 8.

Slices: design [PR #1017](https://github.com/tya5/chrona/pull/1017) (`622bed98`); C1013-1 (resolver, tests, specifications) [PR #1022](https://github.com/tya5/chrona/pull/1022) (`584b7cc2`), CI green before merge (conformance, three pytest shards, newest-Python reproduction, derived-ready).

## Literal issue acceptance

### Issue #1013

- Source: [Issue #1013](https://github.com/tya5/chrona/issues/1013)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A free label (or mark) on a translucent Rect (a label chip or region frame with opacity below 1) is composited over the ground beneath it so it is judged on the colour it truly lies on, instead of failing closed. | met | [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py): `_grounds_under` blends each colour of a translucent host over every ground beneath it. [`test_translucent_ground_contrast.py`](../../../tests/unit/chrona/presentation/scene/test_translucent_ground_contrast.py) asserts exact `blend_over` composites for a chip and a region frame; a render of a 0.9-opacity band judged 6 findings on `translucent-over-*` grounds, all legible (image read); [`test_region_frames_render.py`](../../../tests/integration/test_region_frames_render.py) renders a translucent panel. | none |
| 2 | (Assignment) The ground resolution is the one the gate has: `blend_over`, the cone-composited ground, pattern substrate and ink; beneath ground a band, pattern, texture, cone, region frame or canvas. | met | Same resolver in [`contrast_policy.py`](../../../src/chrona/presentation/scene/contrast_policy.py) reuses `blend_over`, `_cone_overlay`/`_under_cone` and `_host_ink`; tests cover a band, an opaque gradient, a region frame, a canvas texture, a catalogue pattern, a patterned translucent chip, stacked hosts, a cone before and after the chip, and a label straddling the cone edge. | none |
| 3 | (Assignment) Synthetic tests only: translucent chip over light and dark canvas, over a band tint, over a pattern, worst-of-grounds. | met | 21 hand-built Scene tests in [`test_translucent_ground_contrast.py`](../../../tests/unit/chrona/presentation/scene/test_translucent_ground_contrast.py), no `examples/` input; the texture and pattern tests assert the ink composite decides; 13 mutations (host colour alone, beneath ground ignored, first group or ground only, cone before or after dropped, opacity ignored, class widened or narrowed, floor lowered, opacity refusal removed, host ink dropped, gradient sample ignored) were each killed (one needed an added straddle test). | none |
| 4 | (Assignment) Fail-closed stays for what is genuinely unresolvable, documented exactly. | met | [Specification 46 section 8](../../specification/46-completed-scene-paint.md) lists: a host with opacity outside [0, 1], non-hex fill, unsampleable gradient or such a ground beneath; a decoration on a translucent host; note prose on a non-opaque box (Spec 08 C4); a translucent canvas (`E_SCENE_CONTRAST_PAINT`). Each has a test. | none |
| 5 | (Assignment) #995 classes kept: text legibility blocks, decoration warns; no gate weakened. | met | No floor, class or code changed; in [`test_translucent_ground_contrast.py`](../../../tests/unit/chrona/presentation/scene/test_translucent_ground_contrast.py) `test_text_on_a_host_that_cannot_be_read_blocks_whatever_the_decoration_severity` and `test_a_decoration_on_a_translucent_host_keeps_its_warning_and_is_not_composited` pass; the floor-lowered mutation is killed. | none |
| 6 | (Assignment) Specifications 46 and 50 and the diagnostic ledgers updated; mutation-checked; one rendered image read if rendered. | met | Specifications 46 (two statements and a new paragraph), 50, 07 and the [skills diagnostics row](../../../skills/chrona/references/diagnostics.md) updated; the generated ledgers (`inventory.md`, `presentation-contrast.md`) are bot-regenerated (the contrast report is unchanged: 0 errors, 0 warnings; the inventory only moves a code location). Image: the synthetic period-band render, read. | none |
| 7 | (Assignment) The reviewer's `examples/halcyon-1/*target-b*` YAML and #991's files are not edited; findings there go to #987. | met | `git diff --stat origin/main` for [PR #1017](https://github.com/tya5/chrona/pull/1017) and [PR #1022](https://github.com/tya5/chrona/pull/1022) listed only the files named above; no `examples/` file; the corpus report has no new finding, so nothing for #987. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Only the completed-Scene policy changed and it still reads the serialized Scene alone; registry, Layout, Theme and adapters are untouched. No schema, Scene or Theme change; the corpus has no translucent host, so public evidence is unchanged.

Disclosures:

- **Decorations are not composited** (decision J1): a decoration on a translucent host keeps its #995 warning. Reverse: drop one class condition.
- **Note prose stays fail-closed** on a non-opaque note box (J3, Specification 08 C4).
- **Behaviour change for downstream projects:** a label on a translucent chip that used to fail with `E_SCENE_CONTRAST_GROUND_UNSUPPORTED` now passes or fails with `E_SCENE_STATE_TEXT_CONTRAST` and the composited ground reported.
- Four existing tests that asserted the old fail-closed rule were moved to the new rule, each keeping a case for what remains unreadable.

Exact review-bearing-main three-OS CI and the newest-Python materializer run must pass before closing #1013; that run is recorded in the closing comment.
