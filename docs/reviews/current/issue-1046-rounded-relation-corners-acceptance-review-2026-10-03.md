<!-- chrona:literal-acceptance/v1 -->

# Issue #1046: rounded corners on orthogonal relation routes, acceptance review

Source: [Issue #1046](https://github.com/tya5/chrona/issues/1046), re-fetched 2026-10-03 after the merges (body unchanged; comments: this work's claim, decision and status lines, no new acceptance rows). Work record: [issues-1042-1046-1044-relation-terminals-and-rounded-routes-2026-10-03.md](../planning/active/issues-1042-1046-1044-relation-terminals-and-rounded-routes-2026-10-03.md).

Slices: design [PR #1058](https://github.com/tya5/chrona/pull/1058); implementation [PR #1071](https://github.com/tya5/chrona/pull/1071) (`fcd411ee`), CI green before merge.

## Literal issue acceptance

### Issue #1046

- Source: [Issue #1046](https://github.com/tya5/chrona/issues/1046)
- Observed: 2026-10-03

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The Theme knob exists. With it absent or `0`, every committed slide is byte-identical; this is the no-change proof (#575). | met | The knob is the existing optional Theme metric `timeline.relation.cornerRadius` (absent means 0; [`sources.py`](../../../src/chrona/presentation/layout/sources.py)). [`test_relation_rounded_corners.py`](../../../tests/unit/chrona/presentation/scene/test_relation_rounded_corners.py) asserts absent and `0` give the same points and no curve commands. Of the committed slides, only the 4 that already declared a radius changed (see disclosures); every slide without a radius was byte-identical on regeneration. | none |
| 2 | Synthetic tests cover the clamp: a long segment pair gets the full r, and a short step gets the reduced r. They also cover straight terminal segments, and identical SVG and PNG geometry. | met | [`test_relation_rounded_corners.py`](../../../tests/unit/chrona/presentation/scene/test_relation_rounded_corners.py), no `examples/` input: full r on long legs, reduced r on a 5 px and a 9 px step, terminal run (unit and surface level), SVG `Q` commands equal the Scene commands and the resvg PNG has ink on the arc and none on the square corner. Mutation checks (half-leg clamp, terminal run, obstacle check, non-turn skip) each fail a test and were restored. | none |
| 3 | The contrast, crossing and obstacle gates use the rounded path. | met | Measured: no Scene gate reads relation geometry ([`perceptibility.py`](../../../src/chrona/presentation/scene/perceptibility.py) measures Text and Rect). The rules that read relation paths are Layout's: route search, the new arc check ([`surface_routes.py`](../../../src/chrona/presentation/layout/surface_routes.py) `corner_arc_blocker`: a blocked arc halves to square, host marks exempt) and label placement against the registered route obstacles, which now include the arc chords. Tests: halving, square fallback and host exemption. Contrast depends on paint, not geometry. | none |
| 4 | Target B and the bundled default use 4 px, and the reviewer reviews the rendered evidence. | deferred | Bundled default met: `editorial-readable-default` (and its identical example mirror) declare 4. Target B is the reviewer's file ([`target-b.yaml`](../../../examples/halcyon-1/themes/target-b.yaml)) and was not edited; locally with 4 px it changes 20 of 24 route paths and draws rounded corners. The reviewer's adoption and review are a reviewer-owned step. | [#1077](https://github.com/tya5/chrona/issues/1077) |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Layout owns the arcs; Scene carries `points` (the orthogonal polyline) and `pathCommands`; adapters serialize; no schema change.

Disclosures:

- Discovered at baseline: rounding already existed (radius 3 in `mission-light`, `control-room-dark`, `briefing`), so the work is the terminal run, the obstacle check and the default.
- Corpus effect: 31 of 564 relation paths on the 4 slides that already set a radius changed; the groups are (a) a collinear point no longer emitted as a degenerate quadratic (identical ink) and (b) a corner beside a short last leg now square. `01-mission-brief` before and after was read and is identical to the eye; `06-flight-readiness` (group a, one path), `08-gallery-dark` and `09-gallery-mono` (the same paths as `01`) were not read. The default theme is used by no committed slide.
- The task note expected the 4 px default to change every slide with routes; with the knob a Theme choice it does not (other presets keep 0).

Exact review-bearing-main three-OS CI must pass; #1046 stays open until #1077 resolves row 4.
