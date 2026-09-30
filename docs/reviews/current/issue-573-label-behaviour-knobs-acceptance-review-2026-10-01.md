<!-- chrona:literal-acceptance/v1 -->

# Issue #573 — label behaviour knobs acceptance review

Source: [Issue #573](https://github.com/tya5/chrona/issues/573), observed 2026-10-01. Design: [#573 design](../../design/issue-573-label-behaviour-knobs-design-2026-09-30.md), [implementation plan](../../planning/active/issue-573-label-behaviour-knobs-implementation-plan-2026-09-30.md) and [architecture review](issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md), published in [PR #659](https://github.com/tya5/chrona/pull/659), merged as [`e7c09a14`](https://github.com/tya5/chrona/commit/e7c09a140419b6c0084f93a018ca8b609d7be71e). Product slices: [PR #663](https://github.com/tya5/chrona/pull/663) merged as [`8c590276`](https://github.com/tya5/chrona/commit/8c590276224e752f76c75466b16a861f44c8b007) ([PR CI](https://github.com/tya5/chrona/actions/runs/36734497497)); [PR #673](https://github.com/tya5/chrona/pull/673) merged as [`9d4cd8d4`](https://github.com/tya5/chrona/commit/9d4cd8d4a25469182645109e3a51e4f4d3741225) ([PR CI](https://github.com/tya5/chrona/actions/runs/36737045161)).

## Literal issue acceptance

### Issue #573

- Source: [Issue #573](https://github.com/tya5/chrona/issues/573)
- Observed: 2026-10-01

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A declared metric, for example Theme `metrics.memberLabel.maxEndGapEm` or a Layout equivalent, defaulting to 2, replaces the constant in both call sites. A synthetic test shows two values giving two bounds. | met | The Layout equivalent is `reviewSurface.memberNames.maxEndGapEm` (number 0 to 100, default 2) in the [layout-profile v0.9 schema](../../../schemas/layout-profile-v0.9.schema.yaml), added in place with `additionalProperties: false`. The constant is gone from the one call site in [`surface_member_labels.py`](../../../src/chrona/presentation/layout/surface_member_labels.py); the issue cites two, and the composer split (#592) had already left one. The [unit tests](../../../tests/unit/chrona/presentation/layout/test_member_names_profile_knobs.py) give the reach for each declared value with no corpus input; the [render test](../../../tests/integration/test_member_names_render_knobs.py) shows `0.5` and `4` giving two bounds and `0` removing end placement. | — |
| 2 | A declared label-search policy (for example `memberNames.search` choosing between `side-band` and `full-band`) replaces the implicit coupling. The defaults keep today's output byte-identical. A synthetic test covers both values on lane and non-lane rows. | met | `reviewSurface.memberNames.search` (`side-band` or `full-band`) replaces the coupling when declared; when omitted the old rule (`full-band` for a lane row under `rowDistribution: fill`) still applies. The [render test](../../../tests/integration/test_member_names_render_knobs.py) covers both values on lane and automatic rows under `pack` and `fill`, and asserts an explicit `maxEndGapEm: 2` renders byte-identically to the default. The [unit tests](../../../tests/unit/chrona/presentation/layout/test_member_names_profile_knobs.py) show manifest bytes are unchanged when the knob is absent, and `regenerate_public_examples --check` and `derived_evidence --check` showed no derived change. | — |
| 3 | Spec 50 states the default and the knob, not a fixed number. | met | [Spec 50](../../specification/50-constraint-driven-gantt-surface-quality.md) now describes `reviewSurface.memberNames`, both members, their defaults and the omitted-member rule, and says a derived Layout Profile declares its own. | — |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout-only: the knob lives in the Layout Profile, is read at the single call site, reaches it through `LayoutManifest.member_names` (serialised only when declared), and changes no Scene, adapter or public slide. Byte identity proves only that the defaults are unchanged, not that labels are good.

Disclosures, all in the [architecture review](issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md):

- **The design's decision 3 is not implemented.** Measuring the end gap from the item's last own drawn mark changed five public slides in a prototype (`aster-ssd/overview` and four HALCYON-1 gallery and brief slides; in `aster-ssd/overview` a suppressed `ftl` label appears). It contradicts the byte-identical default and is not an acceptance row. It stays a design amendment for an owner decision; no issue is closed on it.
- **One value bounds two distances.** `maxEndGapEm` sets both the end gap and the nearest-perimeter association distance, because a second constant of two em at the same call site would have made any value above 2 inert. The name is narrower than its effect; renaming or splitting it is an open public-name decision.
- **Non-lane `full-band` has no production evidence.** It runs without the one-stagger-step cap on automatic rows; Spec 50 says so and the render test pins the wiring only.
- **The render test builds its input from a corpus example.** Its lane and automatic setups are derived from the controller-z example's View and Layout; the knob semantics themselves are proven by the corpus-free unit tests.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #573; record that run in the issue closing comment.
