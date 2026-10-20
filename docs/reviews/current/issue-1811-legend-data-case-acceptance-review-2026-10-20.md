# Issue1811 — legend wording versus data

Source `673cdb8f833f95671f2b602108f609e8c0eccb51`;
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
The [actual CLI PNG](assets-1811/legend-data-case.png) was inspected: `Aiko`
stays capitalized beside lower-case authored/built-in keys. It renders the
first integration fixture at1800×1000 with the same resources/Actual input;
its pre-existing synthetic Actual-on-Plan contrast warnings are unchanged,
not evidence for reviewer-owned palette row2.
Required before release: current-ready integration, final-head CI, the official
generated artifact's per-slide count table and exact review-containing main's
three-OS release. No generated output is authored in this slice.
