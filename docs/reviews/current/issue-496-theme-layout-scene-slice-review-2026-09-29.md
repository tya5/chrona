# #496 Slice 2 Theme/Layout/Scene review

**Public implementation:** `ce54c692e304e62565604611ed611ec26466f8ab` (PR [#524](https://github.com/tya5/chrona/pull/524)). **Release gate:** [CI run 36474240641](https://github.com/tya5/chrona/actions/runs/36474240641) passed on macOS, Ubuntu, Windows, and newest-Python public materializers. This checkpoint is not issue acceptance.

Theme v0.13/v0.14 closes exact catalogue glyph and pattern references. Layout completes glyph fit and Rect tile region, origin, clip and routes; Scene v0.7 projects those facts and paint; SVG serializes them, and PNG uses the same SVG path. Existing Scene v0.6 and 29 public SVG materializers remain byte-identical. The Scene primitive-delivery and import-direction checks pass. Focused presentation tests (667) and catalogue-specific regressions pass locally. The first CI attempt found duplicate wheel inclusion on all three OSes; the fix keeps `schemas/` as the single source authority under Hatch's existing force-include. The final CI matrix and local wheel build passed.

| Literal issue criterion | Status | Evidence / remaining gate |
| --- | --- | --- |
| A catalogue can hold `glyph` and `pattern` entries, validated and normalized with licence and notice. | met | Slice 1 PR #523 and its [review](issue-496-catalogue-import-slice-review-2026-09-29.md). |
| A Theme can bind a catalogue glyph as a milestone or gate shape, reusing #464's glyph path, and a pattern as a role's fill. SVG and PNG render them identically, and the perceptibility and contrast gates see their effective paint. | deferred | Slice 2 structural and paint-gate tests pass; Slice 3 copied-preset visible SVG/decoded PNG evidence remains. |
| A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags. | deferred | Slice 3 wheel bundle and public CLI evidence. |
| A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile. | deferred | Slice 3 packaged inventory and visible render. |
| A missing asset reference fails with a Theme pointer and the `set:name`. | met | PR #524 Theme closure test asserts `/body/values/symbol/value/shape/catalog` and `missing:pin`. |

The issue remains open until the Slice 3 public artifact and final literal acceptance review pass.
