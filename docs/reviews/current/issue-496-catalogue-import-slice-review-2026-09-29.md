# #496 Slice 1 catalogue/import review

**Public base:** `e0b56617ba7c678af579819ec231eddc2a220e55` (PR [#523](https://github.com/tya5/chrona/pull/523)). **Next:** [Slice 2–4 implementation plan](../../planning/active/issue-496-theme-asset-catalogues-implementation-plan-2026-09-28.md). This is a slice checkpoint, not issue acceptance.

The v0.4 catalogue and source schemas, importer, normalizer, CLI, packaged schemas, canonical fixture and diagnostics are published. Exact `set:name` validation, licence/notice rules, density precision, and atomic import are covered by focused tests. The generated canonical fixture and diagnostic inventory were reviewed after the cross-OS numeric precision fix. Local conformance passed; [CI run 36469440592](https://github.com/tya5/chrona/actions/runs/36469440592) passed on Ubuntu, macOS, Windows and newest-Python public materializers. No Layout, Scene, SVG or preset behavior was accepted in this slice. The boundary remains catalogue normalization in the icon layer, not renderer-side asset interpretation.

| Literal issue criterion | Status | Evidence / remaining gate |
| --- | --- | --- |
| A catalogue can hold `glyph` and `pattern` entries, validated and normalized with licence and notice. | met | v0.4 schemas, importer/normalizer tests and canonical fixture in PR #523. |
| A Theme can bind a catalogue glyph as a milestone or gate shape, reusing #464's glyph path, and a pattern as a role's fill. SVG and PNG render them identically, and the perceptibility and contrast gates see their effective paint. | deferred | Slice 2 render and paint-gate evidence. |
| A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags. | deferred | Slice 3 bundle/copy/render evidence. |
| A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile. | deferred | Slice 3 starter inventory and rendered preset. |
| A missing asset reference gives the exact Theme pointer and `set:name`. | deferred | Slice 2 Theme closure test and final acceptance. |

The issue remains open until the final visible-output and release gates pass.
