# Heading and frame-glyph glow acceptance review

<!-- chrona:literal-acceptance/v1 -->

Implemented in [PR #1246](https://github.com/tya5/chrona/pull/1246), merged as
[`127f1d83848f9f5db2ee995237f5c8a456fe4d2e`](https://github.com/tya5/chrona/commit/127f1d83848f9f5db2ee995237f5c8a456fe4d2e).
Final PR head [`ecbd8fce37eb6583770615b0690fe6cf0a85bbf2`](https://github.com/tya5/chrona/commit/ecbd8fce37eb6583770615b0690fe6cf0a85bbf2)
passed [PR CI run 37811509356](https://github.com/tya5/chrona/actions/runs/37811509356).
The exact published main containing the implementation and original literal acceptance table is
[`09572169c8b9f14614c7d6671f004a3ac0fdddda`](https://github.com/tya5/chrona/commit/09572169c8b9f14614c7d6671f004a3ac0fdddda);
[release run 37817234594](https://github.com/tya5/chrona/actions/runs/37817234594)
passed on that SHA (three-OS pytest/conformance/wheel smoke, MCP floor, and
newest-Python reproduction). Shared snapshot artifact
[11564899965](https://github.com/tya5/chrona/actions/runs/37811509356) has GitHub
artifact digest `sha256:e4d90b85c846a01366fbf8ef71b2d0e442e917e164c818b3c6381d510b3be2f4`.
It contains 145 before/after paths (68 SVG, 68 Scene); there were no additions
or removals. SVGs and Scenes were byte-identical; the only report change was
diagnostic source-location movement, with an empty normalized `:line:col`
diff. All 145 published-main blobs were independently verified against the
snapshot.
[Living design, architecture review and plan](https://github.com/tya5/chrona/issues/1237#issuecomment-6061351395).

## Literal issue acceptance

### Issue #1237

- Source: [Issue #1237](https://github.com/tya5/chrona/issues/1237)
- Observed: 2026-10-08

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A Theme with glow on `heading` and on `frame-glyph` emits the glow paint for the title run and for each glyph in the frame run. | met | [Actual Scene, SVG filters and PNG halos for title, kicker, subtitle and every dynamic-role glyph](../../../tests/integration/test_heading_frame_glyph_glow.py); actual PNG inspected. | none |
| 2 | A baseline profile omits the glow under the existing ladder. | met | [Fill-only neutral glyph catalogue: optional glow omitted, text and all glyph ink retained; required glow fails at exact pointer](../../../tests/integration/test_heading_frame_glyph_glow.py). | none |
| 3 | The defaults are byte-identical. | met | [Synthetic absent-glow, ordinary-opacity-only and fidelity-only SVG/Scene byte assertions](../../../tests/integration/test_heading_frame_glyph_glow.py); [legacy timeline/network fallback](../../../tests/integration/test_title_ink.py). The exact-head snapshot and 145-blob published-main comparison above passed. | none |
| 4 | Marquee adopts it. | deferred | [Reviewer-owned adoption, explicitly not a dev closing gate](https://github.com/tya5/chrona/issues/454). No examples changes authored. | [Reviewer successor #1233](https://github.com/tya5/chrona/issues/1233) |

## Programme-level criteria (optional)

Combined glow/frame-consumer, annotation kind/bar/stamp, adapter integration,
whole/split heading/network, kicker/Scene-boundary/ownership and semantic
reachability tests: 217 passed. After the predecessor's vocabulary registration
fix and reviewer public-base update, the affected glow unit/adapter tests passed
again: 50 tests in 24.45s. No glow product code changed during that refresh.
Schema annotations and diff checks passed. The final exact-main release above
supplies the publication and three-OS evidence.
Layout measurements and completed geometry do not change. Scene selects
explicit glow roles and requires their own fill; adapters serialize existing
paint. Generic all-or-none glow validation and contrast floors remain intact;
gradient/shadow stay excluded from the newly admitted roles.
The network title also emits the heading glow filter and rejects missing own fill.
