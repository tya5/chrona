<!-- chrona:literal-acceptance/v1 -->
# Issues #1164–#1165 — title ink and named frame acceptance

Ready base: `8f5de096e3601507639a9ec3b3a145656159b7c5`.
[1164 plan and release receipts](https://github.com/tya5/chrona/issues/1164#issuecomment-5998117464)
and [1165 plan and release receipts](https://github.com/tya5/chrona/issues/1165#issuecomment-5998117881)
identify the published product commit, PR, generated batch, and exact-main release.
Specs 07/08/33/49 retain Theme paint selection, Layout geometry and completed role,
Scene projection/paint closure, and adapter serialization. No examples are edited.

Focused verification: 147 tests across title/frame integration, Layout frame,
Scene capability, semantic contrast, Theme resolution and role-consumer suites;
62 Theme-token/placement tests. Schema equivalence: PASS, L1 additive=1/equal=37,
L2 511 tracked/411 mapped with four existing invalid fixtures, L3 739 probes;
no new invalid document. Local conformance has one failure:
`E_DIAGNOSTIC_INVENTORY_STALE` from changed source locations/new validation sites;
all other checks pass. CI regenerates that report in its shared snapshot; it is
not hand-edited in this PR. Full CI and actual corpus batch remain required.

## Literal issue acceptance

### Issue #1164

- Source: [body](https://github.com/tya5/chrona/issues/1164)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | `heading.fill` sets the title Text fill; without it, the Scene bytes are unchanged. The same holds for `subtitle`. | met | [Title integration](../../../tests/integration/test_title_ink.py): both own inks and opacities; exact completed Text primitives and SVG bytes without fill, including opacity-only declarations | — |
| 2 | Layout bounds and lines are identical with or without the fill. | met | [Title integration](../../../tests/integration/test_title_ink.py): bounds, lines, font size/family/asset identity unchanged | — |
| 3 | `heading.stroke` is `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at its pointer. | met | [Title integration](../../../tests/integration/test_title_ink.py): exact `/body/colorBindings/heading.stroke` | — |
| 4 | A low-contrast title is reported per the contrast policy. | met | [Title integration](../../../tests/integration/test_title_ink.py): title/subtitle warning records, disabled warnings, blocking error and policy pointer on actual rendered grounds | — |
| 5 | Yuya adopts it: gold title. | not met | [Reviewer-owned target #1116](https://github.com/tya5/chrona/issues/1116) / [PR #1123](https://github.com/tya5/chrona/pull/1123); synthetic support does not prove adoption | — |

### Issue #1165

- Source: [body](https://github.com/tya5/chrona/issues/1165)
- Observed: 2026-10-06

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Two sibling frames with different `paint` values emit Rects with their own fills. | met | [Named-frame integration](../../../tests/integration/test_named_region_frames.py): distinct Scene roles/fills and actual SVG Rect inks | — |
| 2 | A frame without `paint` is byte-identical. | met | [Named-frame integration](../../../tests/integration/test_named_region_frames.py): unchanged completed frame primitives and exact SVG bytes with unused named roles; [placement fixture](../../../tests/unit/chrona/presentation/layout/test_region_frame_paint.py) | — |
| 3 | A patterned inner frame inside a stroked outer frame renders both. | met | [Named-frame integration](../../../tests/integration/test_named_region_frames.py): actual SVG pattern and outer outline, ordered nested painted bounds | — |
| 4 | A missing named role omits only that frame. | met | [Named-frame integration](../../../tests/integration/test_named_region_frames.py): missing role and absent base role preserve the other named frame | — |
| 5 | Text on a named frame is gated on that frame's fill. | met | [Named-frame integration](../../../tests/integration/test_named_region_frames.py): title ground is the selected frame; selected/unselected named role warning checks | — |
| 6 | A malformed token is a schema error. | met | [Integration](../../../tests/integration/test_named_region_frames.py) and [profile tests](../../../tests/unit/chrona/presentation/layout/test_region_frame_profile.py): shared slug validation and exact root/override paint pointers | — |
| 7 | Yuya adopts it. | not met | [Reviewer-owned target #1116](https://github.com/tya5/chrona/issues/1116) / [PR #1123](https://github.com/tya5/chrona/pull/1123); actual plaque/rule/board adoption remains unverified | — |

## Programme-level criteria (optional)

Keep both issues open until actual Yuya adoption, the reviewed CI Scene/SVG
side-effect batch, required PR checks, and three-OS release on the exact published
main containing this review are verified. Existing explicit subtitle fills may
intentionally repaint subtitles; disclose counts instead of adapting the corpus.
