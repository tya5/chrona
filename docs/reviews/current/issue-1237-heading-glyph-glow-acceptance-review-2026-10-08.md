# Heading and frame-glyph glow acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implementation `5e891e73660c48081bd6c443fb970b3b14bc44ef`; ready-base merge
`87b4ea07f547bbabb75209501a2659a407b4a11a` incorporates main
`3e7a57db1cf4b148b6ee6d4c896708f86f9cea69`.
[Living design, architecture review and plan](https://github.com/tya5/chrona/issues/1237#issuecomment-6061351395).
Release pending predecessor merges, final-base PR CI/shared snapshot and exact
published-main three-OS gate. Do not close yet.

## Literal issue acceptance

### Issue #1237

- Source: [Issue #1237](https://github.com/tya5/chrona/issues/1237)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A Theme with glow on `heading` and on `frame-glyph` emits the glow paint for the title run and for each glyph in the frame run. | met | [Actual Scene, SVG filters and PNG halos for title, kicker, subtitle and every dynamic-role glyph](../../../tests/integration/test_heading_frame_glyph_glow.py); actual PNG inspected. | none |
| 2 | A baseline profile omits the glow under the existing ladder. | met | [Fill-only neutral glyph catalogue: optional glow omitted, text and all glyph ink retained; required glow fails at exact pointer](../../../tests/integration/test_heading_frame_glyph_glow.py). | none |
| 3 | The defaults are byte-identical. | met | [Synthetic absent-glow, ordinary-opacity-only and fidelity-only SVG/Scene byte assertions](../../../tests/integration/test_heading_frame_glyph_glow.py); [legacy timeline/network fallback](../../../tests/integration/test_title_ink.py). Public snapshot remains a release gate. | none |
| 4 | Marquee adopts it. | deferred | [Reviewer-owned adoption, explicitly not a dev closing gate](https://github.com/tya5/chrona/issues/454). No examples changes authored. | [Reviewer successor #1233](https://github.com/tya5/chrona/issues/1233) |

## Programme-level criteria (optional)

Focused tests: 48 glow/frame-consumer unit, 10 new adapter integration,
84 heading/kicker/Scene-boundary/ownership regression and 4 semantic-reachability
tests passed. Schema annotations and diff checks passed.
Layout measurements and completed geometry do not change. Scene selects
explicit glow roles and requires their own fill; adapters serialize existing
paint. Generic all-or-none glow validation and contrast floors remain intact;
gradient/shadow stay excluded from the newly admitted roles.
