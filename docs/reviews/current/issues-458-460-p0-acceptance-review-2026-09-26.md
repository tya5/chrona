<!-- chrona:literal-acceptance/v1 -->

# Release review — P0 as-of placement and shipped preset (#458, #460)

## Literal issue acceptance

### Issue #458

- Source: [Issue #458](https://github.com/tya5/chrona/issues/458)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On `04-tvac-slip` and `07-replan-baseline`, the as-of label is beside its line. | met | Public [04 SVG](../../../examples/halcyon-1/generated/04-tvac-slip.svg) and [07 SVG](../../../examples/halcyon-1/generated/07-replan-baseline.svg) rendered and visually inspected; each text box is centered above its as-of line in the mark-clear axis/timeline seam. | — |
| 2 | No committed Scene contains a primitive recorded as suppressed. | met | [Exact three-family identity gate](../../../src/chrona/presentation/scene/perceptibility.py) and [focused fixtures](../../../tests/unit/chrona/presentation/scene/test_perceptibility.py); 21 committed Scenes, 0 errors. | — |

### Issue #460

- Source: [Issue #460](https://github.com/tya5/chrona/issues/460)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | `chrona render demo/project.yaml --preset <copy of each library entry>` succeeds for all five entries, on a fresh `chrona init demo`. | met | [Manifest-derived CLI matrix](../../../tests/cli/test_cli.py) runs all five with no `--actual` or `--visual-profile` exception; 6 relevant CLI cases passed including required-capability rejection. Default elevated SVG was rendered and visually inspected. | — |
| 2 | A check fails if a library entry cannot render the starter project. | met | The same parametrization reads every entry from the packaged [library manifest](../../../src/chrona/resources/presets/library.yaml); each case calls public `init`, `preset copy`, and `render`, requiring SVG output and all starter object IDs. | — |

## Programme-level criteria (optional)

- Implementation base: `a3638af151cc549d7f06963fba4c30e3488d91f6` on public `main`.
- Focused Layout/Scene tests: 65 passed; all CLI tests: 56 passed;
  visual-capability unit tests: 14 passed. Generated-output properties:
  100 passed, 18 optional-font skips.
- All 21 public materializer contexts reproduced byte-identically after the
  two HALCYON scenes and elevated Scene/SVG were regenerated.
- Conformance passed, including the 21-Scene perceptibility gate and refreshed
  diagnostic inventory.
- The fallback-only correction preserved all previously fitting corpus as-of
  labels and restored HALCYON 04's original TVAC member-label choice. Only
  HALCYON 04/07 as-of output changes remain in the final correction.
- Rich elevated SVG element IDs changed with the Theme resource identity, but
  its rasterized PNG bytes stayed identical (SHA-256
  `08af1421da2d15ad06f70fe99dd8276048edf38a43acfafcefe977c2788bd5a9`).
- The prior [red CI run](https://github.com/tya5/chrona/actions/runs/36213509375)
  exposed one text-over-mark acceptance failure on HALCYON 07. The
  [mark-clear design correction](../../design/issue-458-as-of-mark-clearance-correction-2026-09-26.md)
  and [fallback-only refinement](../../design/issue-458-fallback-only-candidate-correction-2026-09-26.md)
  address it. Final [CI run 36214290504](https://github.com/tya5/chrona/actions/runs/36214290504)
  passed Ubuntu, macOS, and Windows conformance/full pytest/wheel-smoke,
  plus newest-Python public materializer reproduction.

## Architecture conclusion

Layout owns the as-of overflow fallback and collision reranking; Scene only
projects visible placements, and the serialized-Scene observer enforces exact
suppression identities. Theme declares elevated effects optional only where
the flat fallback is complete; Scene applies profile-dependent omission;
adapters do not choose paint. No compatibility layer, preset target authority,
or new rendering path was introduced.
