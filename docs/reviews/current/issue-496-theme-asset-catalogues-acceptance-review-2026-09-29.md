<!-- chrona:literal-acceptance/v1 -->

# #496 Theme asset catalogues acceptance review

**Source:** [Issue #496](https://github.com/tya5/chrona/issues/496), observed 2026-09-29; no later comments. **Public implementation:** PR [#523](https://github.com/tya5/chrona/pull/523) (`e0b56617`), PR [#524](https://github.com/tya5/chrona/pull/524) (`ce54c692`), and PR [#525](https://github.com/tya5/chrona/pull/525) (`29de2cd6`). **Release CI:** [run 36476714999](https://github.com/tya5/chrona/actions/runs/36476714999), all four jobs passed. **Predecessors:** [catalogue/import review](issue-496-catalogue-import-slice-review-2026-09-29.md), [Theme/Layout/Scene review](issue-496-theme-layout-scene-slice-review-2026-09-29.md).

## Literal issue acceptance

The `met` rows describe published implementation evidence after PR #525's CI and merge.

### Issue #496

- Source: [Issue #496](https://github.com/tya5/chrona/issues/496)
- Observed: 2026-09-29

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A catalogue can hold `glyph` and `pattern` entries, validated and normalized with licence and notice. | met | [PR #523](https://github.com/tya5/chrona/pull/523) contains the v0.4 importer; [PR #525](https://github.com/tya5/chrona/pull/525) ships source, normalized catalogue, MIT notice, hashes and reproducibility test. | — |
| 2 | A Theme can bind a catalogue glyph as a milestone or gate shape, reusing #464's glyph path, and a pattern as a role's fill. SVG and PNG render them identically, and the perceptibility and contrast gates see their effective paint. | met | [PR #524](https://github.com/tya5/chrona/pull/524) covers Layout→Scene projection and effective paint; [PR #525](https://github.com/tya5/chrona/pull/525) tests the public SVG/decoded PNG pin, halftone, contrast and perceptibility. | — |
| 3 | A builtin preset can declare catalogues and a detail profile. `chrona preset copy` copies them with notices, and `chrona render --preset` uses them with no extra flags. | met | [PR #525](https://github.com/tya5/chrona/pull/525) tests exact copy, byte-identical builtin/copied SVG without asset flags, and installed-wheel smoke. | — |
| 4 | A builtin starter catalogue ships the glyphs and patterns listed above. At least one builtin preset uses a glyph and a pattern, and at least one ships a legend through its detail profile. | met | [PR #525](https://github.com/tya5/chrona/pull/525) verifies seven glyphs and halftone, seigaiha, three dither densities and dense hatch; `technical-print` renders pin, halftone and legend. | — |
| 5 | A missing asset reference fails with a Theme pointer and the `set:name`. | met | [PR #525](https://github.com/tya5/chrona/pull/525) asserts `E_THEME_ASSET_REFERENCE`, the exact Theme pointer, `missing:pin`, and no output. | — |

## Programme-level criteria (optional)

None.

## Release and architecture conclusion

PR #525 merged as `29de2cd6` after CI passed newest-Python public reproduction and macOS/Ubuntu/Windows conformance, full pytest, and wheel gates. Focused commands: `python -m pytest -q tests/integration/test_builtin_theme_assets.py tests/integration/test_packaged_resources.py` (8 passed), `python -m pytest -q tests/unit/chrona/usecases/test_preset_library_catalogues.py` (8 passed), `python tools/schema_annotations.py`, `python tools/declared_value_inventory.py --check`, `python tools/wheel_smoke.py`, and `python tools/regenerate_public_examples.py --check --jobs 4` (29 unchanged slides). The first PR #524 CI failure was duplicate schema wheel inclusion; the corrected CI matrix passed. The wheel includes catalogue, source, manifest, notice and successor schema through ordinary packaged resources. Layout owns completed pattern/glyph geometry, Scene projects and carries paint, adapters serialize, and preset copy only materializes declared members. Specs 07/08/62/64 and the published design corrections remain aligned. All literal criteria are met; there is no deferred successor.
