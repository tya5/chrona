<!-- chrona:literal-acceptance/v1 -->
# Issue #1163 — cross-size stretch acceptance

Product commit: `2470eaeb46300787c00b76d9eddf1a5003a6dd7a`; ready base: `e5b3691f`.
[PR #1171](https://github.com/tya5/chrona/pull/1171) publishes code, tests and this review.
[Current plan and release receipts](https://github.com/tya5/chrona/issues/1163#issuecomment-5996580439) are the live verification authority.
Layout completes sizes through its existing flex resolver; alignment only positions them.
Spec 33 remains authoritative; no schema, View, Theme, Scene, adapter or corpus edits.
The independent pre-existing flow size-completion defect is tracked in [#1170](https://github.com/tya5/chrona/issues/1170).

Focused verification: `.venv/bin/python -m pytest -q tests/unit/chrona/presentation/layout/test_cross_size_stretch.py tests/unit/chrona/presentation/layout/test_intent_engine.py tests/unit/chrona/presentation/layout/test_flexible_track_allocation.py` — **64 passed**.
`.venv/bin/chrona materialize examples/halcyon-1/manifest.yaml --slide overlay-briefing --output <empty-temporary-directory>` passes; actual Scene/SVG are byte-identical to ready main. No `--write` was used.

## Literal issue acceptance

### Issue #1163

- Source: [body](https://github.com/tya5/chrona/issues/1163)
- Observed: 2026-10-05

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A root column with `alignItems: stretch` and a child with `inlineSize: {fixed: N}`: the child is N wide. | met | [Synthetic manifests](../../../tests/unit/chrona/presentation/layout/test_cross_size_stretch.py), including inherited alignment and fixed visible overflow | — |
| 2 | A `fill` child still stretches. | met | [Column/row/overlay fill and fractional fixtures plus distinguishing flow line-height fixture](../../../tests/unit/chrona/presentation/layout/test_cross_size_stretch.py) | — |
| 3 | `alignItems: start` is unchanged. | met | [Start characterization across dimension forms and callers, including unstretched flow fill](../../../tests/unit/chrona/presentation/layout/test_cross_size_stretch.py); non-stretch sizing expressions are preserved | — |
| 4 | The PR includes a corpus side-effect table: every profile with a fixed child under `stretch` changes, and each is listed. | met | [PR count table](https://github.com/tya5/chrona/pull/1171): 28 declared profiles, zero fixed/stretch matches; the only intrinsic candidates are the two overlay-briefing slots, whose actual output is byte-identical | — |

## Programme-level criteria (optional)

Release gate: inspect the complete shared CI corpus against the disclosed table, pass all required exact-head checks, and cite the three-OS release on the exact published main containing this review before closing the issue. Product criteria above do not substitute for that gate; keep the issue open while any required receipt is missing.
