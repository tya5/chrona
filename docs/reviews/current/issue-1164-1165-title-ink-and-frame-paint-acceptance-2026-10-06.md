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
not hand-edited in this PR. Initial CI37339895377 exposed a network-title paint
projection omission; preview failed with `E_THEME_ROLE_REQUIRED`, reproduction
failed for the absent snapshot, and derived-ready propagated the failure.
The network projection now uses the same Theme ink selection; both unmodified
HALCYON network materializers pass and all four Scene/SVG files are byte-identical
to ready main. Registering title
roles also preserves their purpose-based ground gate when used as View cell inks.
Correction verification: 27 title/frame/semantic/network tests pass, including
actual View cells on row-band grounds and the synthetic network title.
CI37341090774 additionally exposed two failures: shard1 applied title ink to
network node labels; shard2 admitted heading glow beyond this slice. Shard3
passed and derived-ready propagated the pytest failures. Layout now completes
distinct title/node-label semantic bindings, preserving node labels' public
purpose and shared ink; heading admits only fill/opacity beyond its prior
measurement/viewer-fit fields. The actual title expectation changes only when
the fixture binds heading.fill. These corrections pass 140 focused tests;
registry reachability/realization and literal review checks pass. Both actual
public network materializers pass and their four Scene/SVG files remain
byte-identical to the validated ready-main renders. Independent architecture
review finds the typed semantic separation consistent with existing ownership.
The 6dca9767 snapshot [batch receipt](https://github.com/tya5/chrona/pull/1172#issuecomment-5998998175)
retains 137 paths:133 byte-identical, one Target B subtitle paint change and
corresponding reports; no geometry/route/wording/ID change or new rendering
diagnostic. Actual SVG/raster review confirms legibility (contrast5.448) and
no clipping/overlap. This is not final-head evidence for the subsequent correction;
latest-head CI and its shared batch remain required.

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
