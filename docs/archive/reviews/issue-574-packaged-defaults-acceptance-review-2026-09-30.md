<!-- chrona:literal-acceptance/v1 -->

# Issue #574 — packaged defaults independent of corpus acceptance review

Source: [Issue #574](https://github.com/tya5/chrona/issues/574), observed 2026-09-30. Design: [#574 design](../../design/issue-574-packaged-defaults-independent-of-corpus-design-2026-09-30.md). Product slices, each merged with [PR CI](https://github.com/tya5/chrona/actions) green: [PR #654](https://github.com/tya5/chrona/pull/654) merged as [`b95b9283`](https://github.com/tya5/chrona/commit/b95b9283f3763de442776f29eec00e67ae9dd9a3) ([CI](https://github.com/tya5/chrona/actions/runs/36715476473)); [PR #655](https://github.com/tya5/chrona/pull/655) merged as [`6c47a280`](https://github.com/tya5/chrona/commit/6c47a280e331fffd5f50581c62ef690fdc4d9938) ([CI](https://github.com/tya5/chrona/actions/runs/36719001713)); [PR #656](https://github.com/tya5/chrona/pull/656) merged as [`22ea2c1c`](https://github.com/tya5/chrona/commit/22ea2c1cb3eb0ced4367325333b493bf396de997) ([CI](https://github.com/tya5/chrona/actions/runs/36722028954)).

## Literal issue acceptance

### Issue #574

- Source: [Issue #574](https://github.com/tya5/chrona/issues/574)
- Observed: 2026-09-30

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every resource a packaged preset or the bundled default needs lives under `src/chrona/resources/presets/**`, including colour schemes. `default_preset_root()` returns the presets root, and no path under `examples/` is read by the default render or by `chrona preset copy`. | met | [`default.yaml`](../../../src/chrona/resources/presets/default.yaml) and [`library.yaml`](../../../src/chrona/resources/presets/library.yaml) name only `bundles/**` paths (no `examples/` text remains in `library.yaml`, asserted by the drift test). [`default_preset_root()`](../../../src/chrona/resources/__init__.py) returns `files("chrona.resources") / "presets"` and `builtin_preset_source_root` has no `examples` branch. The five schemes are packaged as `bundles/<id>/scheme.yaml`. [Guarded-resource test](../../../tests/integration/test_presets_without_examples.py): any `examples` path raises, and the mutation of pointing one library `sourceRoot` back at `examples/halcyon-1` fails it. | — |
| 2 | A test renders every packaged preset and the bundled default with `examples/` absent (for example from the built wheel in a temporary directory). | met | [`test_presets_without_examples.py`](../../../tests/integration/test_presets_without_examples.py) copies and renders the bundled default and every library entry from a starter written by the wheel-owned minimal template, with `chrona.resources.files` refusing `examples`. A locally built wheel (no `resources/examples/controller-z`, `halcyon-1/manifest.yaml` present, size check pass), installed with the render extra, passes [`tools/wheel_smoke.py`](../../../tools/wheel_smoke.py); that step otherwise runs only in the exact-main three-OS run. | — |
| 3 | `gallerySet` names are neutral, or are documented as gallery grouping only. | met | Names are kept, because committed gallery pages use them. The [`preset-library-v0.2` schema](../../../schemas/preset-library-v0.2.schema.yaml) now says a `gallerySet` groups evidence in gallery pages, selects no resource and has no runtime effect (description only, no version change). | — |
| 4 | `--example` enumerates packaged examples from a registry instead of naming one. | met | [`example-registry.yaml`](../../../src/chrona/resources/example-registry.yaml) validated by [`example-registry-v0.1.schema.yaml`](../../../schemas/example-registry-v0.1.schema.yaml), listed in the schema inventory. `chrona init --example` choices come from it, an unregistered id fails with `E_INIT_EXAMPLE` naming the available ids, and a [packaged-resources test](../../../tests/integration/test_packaged_resources.py) asserts the wheel force-include list equals the registered paths (`examples/controller-z` left it). | — |
| 5 | Rendered output is byte-identical before and after the move. | met | Measured before and after I574-1 (recorded in [PR #654](https://github.com/tya5/chrona/pull/654)) with the starter project: the default render, every `preset copy` tree and every preset render give 49 identical SHA-256 hashes, except the five copied `scheme.yaml` files themselves (see the note below). HALCYON-1 and controller-z rendered with all five presets are byte-identical to `main` before the change (10 SVGs). This is a no-behaviour-change proof, not a quality claim. | — |

**Row 5 note.** The packaged `scheme.yaml` files are not byte copies of the example schemes. The existing generic-preset guard forbids a bundle from naming an example project's group values, so the nine `categories` entries keyed by HALCYON-1 and controller-z groups (`bus`, `payload`, `ait`, `ground`, `launch`, `ops`, `factory-team`, `fw-team`, `validation-team`) were removed from all five. Rendering is unchanged for the two corpora and the starter, and the drift test compares each packaged scheme with its example after removing those keys. Two tests that used those names as a palette now use the schemes' generic `series-1..3`; the design records this deviation from its first wording.

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Resources and packaging only: no Layout, Scene or adapter change, and no schema change beyond the new registry schema and one description. Packaged presets can no longer be changed by editing an example, which now fails a drift test. The two readable-default corpus copies stay for the drift guard and carry a declared reason in `tools/corpus_coverage.py`.

**Process note.** The design pack for #574 was published as one consolidated design document. The separate design-plan, architecture-review and implementation-plan files named in the pack's commit subject were not committed, and the design's link to a design plan did not resolve; that link is removed and no plan or review is written after the fact. The slices were reviewed by their PR CI and the local evidence above.

Exact review-bearing-main three-OS CI and newest-Python materializer run must pass before closing #574; record that run in the issue closing comment.
