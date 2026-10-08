# Heading and frame-glyph glow acceptance review

<!-- chrona:literal-acceptance/v1 -->

Prospective integration `f1235a733fe635fb9c461509308f58b76ad5ca41` combines this
implementation with public PR #1245 head `b9ab5eef7963c41e12d4c12c674a3feff22df50b`.
Published ready main is `ba679506c1c8d4661004a480b704530830ea0488` (#1239).
PR #1245 is not merged; final publication will follow #1242 on a ready tip.
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

Combined glow/frame-consumer, annotation kind/bar/stamp, adapter integration,
whole/split heading/network, kicker/Scene-boundary/ownership and semantic
reachability tests: 217 passed in the prospective integration.
Schema annotations and diff checks passed.
Layout measurements and completed geometry do not change. Scene selects
explicit glow roles and requires their own fill; adapters serialize existing
paint. Generic all-or-none glow validation and contrast floors remain intact;
gradient/shadow stay excluded from the newly admitted roles.
The network title also emits the heading glow filter and rejects missing own fill.
