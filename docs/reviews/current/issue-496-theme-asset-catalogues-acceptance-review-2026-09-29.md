<!-- chrona:literal-acceptance/v1 -->

# #496 Theme asset catalogues acceptance review

**Source:** [Issue #496](https://github.com/tya5/chrona/issues/496), observed 2026-09-29; no later comments. **Public implementation:** PR [#523](https://github.com/tya5/chrona/pull/523) (`e0b56617`), PR [#524](https://github.com/tya5/chrona/pull/524) (`ce54c692`), and PR [#525](https://github.com/tya5/chrona/pull/525) (`29de2cd6`). **Release CI:** [run 36476714999](https://github.com/tya5/chrona/actions/runs/36476714999), all four jobs passed. **Predecessors:** [catalogue/import review](issue-496-catalogue-import-slice-review-2026-09-29.md), [Theme/Layout/Scene review](issue-496-theme-layout-scene-slice-review-2026-09-29.md).

## Literal issue acceptance

The `met` rows describe published implementation evidence after PR #525's CI and merge.

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A catalogue can hold `glyph` and `pattern` entries, validated and normalized with licence and notice. | met | v0.4 schema/importer in #523; starter source, normalized catalogue, MIT notice, pinned hashes and reproducibility test in #525. | — |
| 2 | A Theme can bind a catalogue glyph as a milestone or gate shape, reusing #464's glyph path, and a pattern as a role's fill. SVG and PNG render them identically, and the perceptibility and contrast gates see their effective paint. | met | #524 Layout→Scene projection and effective-paint tests; #525 public `technical-print` SVG/decoded PNG integration test asserts visible pin, halftone, three contrast pairs and perceptibility density. | — |
| 3 | A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags. | met | #525 exact-copy/pin test and public CLI test: builtin ID and copied path produce byte-identical SVG with no asset flag; installed-wheel smoke copies notice and renders preset. | — |
| 4 | A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile. | met | #525 manifest verifies pin, lantern, hexagon, star, chest, ticked-circle, diamond; halftone, seigaiha, 12.5/25/50% dither, dense hatch. `technical-print` renders pin and halftone with its legend in SVG and decoded PNG. | — |
| 5 | A missing asset reference fails with a Theme pointer and the `set:name`. | met | #525 public CLI regression asserts `E_THEME_ASSET_REFERENCE`, `/body/values/milestone-symbol/value/shape/catalog`, `missing:pin`, and no output file. | — |

## Release and architecture conclusion

PR #525 merged as `29de2cd6` after CI passed newest-Python public reproduction and macOS/Ubuntu/Windows conformance, full pytest, and wheel gates. Focused commands: `python -m pytest -q tests/integration/test_builtin_theme_assets.py tests/integration/test_packaged_resources.py` (8 passed), `python -m pytest -q tests/unit/chrona/usecases/test_preset_library_catalogues.py` (8 passed), `python tools/schema_annotations.py`, `python tools/declared_value_inventory.py --check`, `python tools/wheel_smoke.py`, and `python tools/regenerate_public_examples.py --check --jobs 4` (29 unchanged slides). The first PR #524 CI failure was duplicate schema wheel inclusion; the corrected CI matrix passed. The wheel includes catalogue, source, manifest, notice and successor schema through ordinary packaged resources. Layout owns completed pattern/glyph geometry, Scene projects and carries paint, adapters serialize, and preset copy only materializes declared members. Specs 07/08/62/64 and the published design corrections remain aligned. All literal criteria are met; there is no deferred successor.
