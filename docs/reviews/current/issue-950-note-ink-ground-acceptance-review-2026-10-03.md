<!-- chrona:literal-acceptance/v1 -->

# Issue #950 — note ink ground at Theme resolution, acceptance review

Source: [Issue #950](https://github.com/tya5/chrona/issues/950), observed 2026-10-03 (body unchanged since filing, re-fetched before this review; the four comments are this session's claim, owner decisions D1 and D2, and state notes, no other contributor's). The three acceptance rows are copied below. Living record: [work record](../../planning/active/issue-950-884-contrast-ground-2026-10-02.md) (shared with #884); living contract [Specification 07](../../specification/07-style-and-theme.md) (note annotation roles). Owner decisions (D1 the ground, D2 which boxes; options, choice, reversal) are [a comment on the issue](https://github.com/tya5/chrona/issues/950#issuecomment-5954365476).

Slices: design, architecture review and implementation plan, [PR #961](https://github.com/tya5/chrona/pull/961) (`c9e3b459`); code, [PR #962](https://github.com/tya5/chrona/pull/962) (`795d1241`). No schema, Scene or diagnostic-code change, so the S0 gate (`python -m tools.schema_equivalence --base-rev origin/main`) is not applicable; it passed in the PR.

## Literal issue acceptance

### Issue #950

- Source: [Issue #950](https://github.com/tya5/chrona/issues/950)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A Theme with a light note box and dark note ink over a dark canvas resolves, and the Scene gate judges the prose on the box. | met | [`color_scheme._state_text_ground`](../../../src/chrona/presentation/color_scheme.py) takes the resolved `annotation-note-box` fill as the ground. Synthetic, no `examples/` input: [`test_annotation_note_ground.py`](../../../tests/integration/test_annotation_note_ground.py) renders the packaged bundle on the dark `control-room-dark` Scheme with a light box and dark ink (canvas `#0B1220`, box `#EAF0FA`); no Scene contrast error; both note-text findings have ground id `annotation-box:*`, ground colour the box, ratio above 14, floor 4.5. [`test_color_scheme.py`](../../../tests/unit/chrona/presentation/test_color_scheme.py) covers the resolution unit cases. The rendered image was read: light note boxes with dark legible prose over a dark canvas. | — |
| 2 | A note ink that fails against its box still fails at Theme resolution, naming the role and the box. | met | Ink `textMuted` on a light box over the same dark canvas (it reads on the canvas, not on the box) is refused with `E_SCHEME_STATE_TEXT_CONTRAST` at `/body/roles/annotation-note-text/fill`, detail `annotation-note-text:annotation-note-box:<ratio>`, in the [integration test](../../../tests/integration/test_annotation_note_ground.py) and three [unit tests](../../../tests/unit/chrona/presentation/test_color_scheme.py) (ink too close, light ink that read on the canvas, translucent ink). The callout box is not a ground (unit test). | — |
| 3 | Every committed Theme resolves as before. | met | `tools/regenerate_public_examples.py --check`: 36 public slides byte-identical, so every committed example Theme resolves; conformance and the full pytest shards are green on [PR #962](https://github.com/tya5/chrona/pull/962). The one existing test fixture whose accent box sat under dark ink (it exercised the ground type, not a committed Theme) now uses `surfaceRaised`. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme resolution now judges note prose on the surface it lies on, the ground the Scene gate already pairs with it, so the static check is the earlier report of the same pair. The canvas remains only where the box has no readable colour (then the note-ground check rejects the Theme anyway). Mutation checks: 7 of 7 killed.

Disclosures:

- **Behaviour change.** A Theme whose note ink passed the canvas but fails its own box is now refused at resolution; it would have failed the Scene gate on the first note drawn. No committed Theme is affected.
- **Judgement call D2.** Only the note box is a ground; the issue's parenthetical named all four annotation boxes. Reversal is one line (recorded on the issue).
- **Evidence limit.** The dark Title Card, Off-World and Marquee note slides themselves belong with the presets and parts work (#718, #453, #883); this issue proves the unblocking on a synthetic Theme.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #950; record that run in the issue closing comment.
