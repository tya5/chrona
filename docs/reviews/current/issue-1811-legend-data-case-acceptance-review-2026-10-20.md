# Issue1811 — legend wording versus data

Source `673cdb8f833f95671f2b602108f609e8c0eccb51`;
precision correction `58c8a4b51` reuses the existing `geometry_sum` contract.
[pre-code plan and architecture review](https://github.com/tya5/chrona/issues/1811#issuecomment-6286123938).
Dev A owns row1; the [reviewer owns row2 and the owner comparison](https://github.com/tya5/chrona/issues/1811#issuecomment-6285598446).

| Literal criterion | Status | Evidence |
| --- | --- | --- |
| A synthetic legend with lower-case design voice and an owner encoding keeps "Aiko" as written; the built-in keys stay lower case. | met locally; release pending | `tests/integration/test_legend_data_case.py` checks actual SVG/Scene for Aiko and mixed-case entity titles, authored/built-in wording, Style title/value separation and real `Other` versus folded wording. `test_legend_literal_measurement.py` checks identical source/placement widths, inline/grid positions, source-preserving ellipsis and literal scope selectors. |
| target-b's owner palette passes its own encoding-contrast floor and separability check against the other legend keys. This is reviewer YAML, and the owner decides the colours (the owner is colour-weak, so choose by lightness steps, not hue alone); a comparison page goes to the owner first. | not met by this slice; reviewer-owned | No palette or example edits. Keep issue1811 open until the reviewer records this row's result or an explicit disposition. |

Layout alone selects wording/literal segments from typed provenance, then shares
their measurement across sizing, fitting and placement. Small-caps wording
retains measured runs while data stays at the role's normal size. Existing
Scene text runs carry the completed result; no adapter, public schema, paint or
routing ownership changes. Specs07/60 state the wording/data boundary. Ordinary
text and `textTransform: none` keep their existing path.

Own-venv focused verification:113 passed across the two new modules and existing
Style scopes, transformed placements, small caps, sources, legend sizing/grid,
slot sizing and realized keys. No local full suite/public-materializer sweep.
The initial CI's float-accumulation gate caught a builtin `sum`; corrected
without changing policy. The gate,30 focused text/legend tests and24 precision/
audit tests pass, including widely separated run widths.
The [actual CLI PNG](assets-1811/legend-data-case.png) was inspected: `Aiko`
stays capitalized beside lower-case authored/built-in keys. It renders the
first integration fixture at1800×1000 with the same resources/Actual input;
its pre-existing synthetic Actual-on-Plan contrast warnings are unchanged,
not evidence for reviewer-owned palette row2.
Published in [PR1816](https://github.com/tya5/chrona/pull/1816), merge
`323d32fec2f1254207102add701eba0401e2c23b`, on trusted ready `76a64952c`.
Final-head [CI39392772621](https://github.com/tya5/chrona/actions/runs/39392772621)
passed all three pytest shards, conformance, MCP floor and newest-Python checks.
Its [official artifact12251005623](https://github.com/tya5/chrona/actions/runs/39392772621/artifacts/12251005623)
has 109 matching before/after paths, no retirements: all 50 SVG and 50 Scene
files are byte-identical (zero route/label/primitive/diagnostic changes on every
public slide). Eight reports are identical; the inventory changes only source
line/column anchors, with identical complete normalized text. No generated
output was authored. Exact review-containing main three-OS release is pending;
row2 remains reviewer-owned regardless of that release.
