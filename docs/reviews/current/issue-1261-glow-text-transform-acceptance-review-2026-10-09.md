<!-- chrona:literal-acceptance/v1 -->

# Issue #1261 — glow filter coordinate frame

Public base: `510fd5f90bcc057d72e575423ec6e114dfa51837`.
Design/architecture/implementation plan: [Status](https://github.com/tya5/chrona/issues/1261#issuecomment-6071940312).
Layout/Scene completed geometry is unchanged; SVG applies text glow once in an
untransformed parent. Text identity, transform, opacity and viewer-fit facts remain on
the child. No schema, corpus or preset changes. Public artifacts have been audited;
The initial-base PR tests passed; latest-base CI and exact-main release remain pending.

## Literal issue acceptance

### Issue #1261

- Source: [Issue #1261](https://github.com/tya5/chrona/issues/1261)
- Observed: 2026-10-09

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A glowing text run with scale 0.5, 0.86 and 1.0: the emitted filter region contains the run's completed bounds plus three times the blur std on each side. | met | [Pipeline scale/filter tests](../../../tests/integration/test_glow_text_transform.py), including Scene bounds, canvas clipping and emitted region; rotated bounds also tested. | — |
| 2 | A rasterised check shows no clipped ink at the end of the run. | met | [Packaged-font raster tests](../../../tests/integration/test_glow_text_transform.py): all opaque final-glyph source pixels survive at each scale. Old main clips 430/430 final-glyph opaque pixels at 0.5 and 756/890 at 0.86; fixed output clips zero. PNGs visually inspected. | — |
| 3 | Non-glow output is byte-identical. | met | [Three pre-fix byte hashes](../../../tests/unit/chrona/presentation/renderers/test_v05_svg.py) match public base. SHA-256 comparison of both [PR snapshot](https://github.com/tya5/chrona/actions/runs/37868103705) archives on `783eb8af` proves all 136 public SVG/Scene files byte-identical on that base. Latest-base public audit remains a release gate. | — |

## Programme-level criteria (optional)

Focused evidence: 96 SVG/Scene/glow/viewer-fit regressions and seven new transform
tests passed. Nested viewer-fit filters, text opacity, textLength and links are covered.
Literal acceptance-review validation passed. Snapshot audit: 145 paths, no changed
SVG/Scene or retirements; only diagnostic source-line inventory changed. PR conformance,
derived-preview, MCP-floor, all three pytest shards and newest-Python reproduction
passed in run 37868103705. Its sole failure was `derived-ready`: main advanced
from `510fd5f9` during CI. Reconcile the ready main and validate the new head;
do not treat that stale-base run as merge acceptance. Ordinary merge of the
published reviewer source `e09c93b3` passed 24 focused transform/viewer-fit tests.
Full release evidence comes from exact-main CI.
