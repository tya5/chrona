# M23 Review Detail visual acceptance — 2026-09-20

**Disposition:** Pass

## Evaluated closure

The Controller Z acceptance resource uses the generic M23 path with an author-editable
Review Detail Profile and a v0.2 Preset override. No project title, profile ID, row ID,
or sample identity is present in renderer code.

The rendered 1600 × 1200 surface contains the existing Plan/Actual Gantt and legend,
three selected-group explanations, a two-row source-labelled observation table, and a
two-entry milestone digest. Project titles and scheduled milestone dates are derived
from the Review Projection. Observation content remains synthetic, literal, and
presentation-only.

## Acceptance evidence

- `controller-z-review-detail.svg` SHA-256:
  `9233604f89028ad220f2f9ca626de487ec91f29bf1d9f7fa88dca7c2767eb2e1`.
- `controller-z-review-detail.png` SHA-256:
  `2e5415c99156f1bdf2afae1402375a9849d7921aca7dcdab4ba5e5ce5bd97ce3`.
- Two independent CLI renders produced byte-identical SVG.
- Raster verification reported zero overflow.
- Visual review confirmed readable group descriptions, dark observation headers on the
  declared header band, visible provenance under each observation row, and milestone
  symbols/dates contained within their slot.
- Source metadata counts are 3 group labels, 3 group descriptions, 6 observation cells,
  2 observation provenance labels, and 2 milestone digest entries.
- The example regression reconstructs the output from YAML, compares exact SVG bytes,
  and proves input resources were not mutated.

This review closes A23 visual acceptance. Final M23 release/reuse review remains the
separate milestone-closing gate.
