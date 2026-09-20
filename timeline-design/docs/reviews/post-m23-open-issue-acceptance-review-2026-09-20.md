# Post-M23 open-issue acceptance review — 2026-09-20

**Disposition:** Pass; GitHub issues closed as completed
**Issues:** #14, #16, #17

## Sequence

The initial design and owning specification corrections were published at `d931813`.
The Aster README regeneration requirement was added before implementation at `f4fcce5`.
When full regression showed that the shared Scene correction also changed the M23
review-detail artifact, implementation stopped and that impact was added to the design
at `1f91d04`. Implementation and regenerated artifacts were then published at
`d123b57`.

## Accepted corrections

- `row-shade` Scene Rects carry the Theme color and opacity. Aster now emits
  `#22364D` at `0.45`; the Controller Z detail surface emits its declared `0.34`.
- Planned/baseline point marks retain their semantic facet but resolve the milestone
  paint and emit the distinct `milestone` output purpose. Aster gate marks and the
  `Planned gate` legend swatch are both `#F3F2EC`.
- A table/timeline surface no longer invents a title rule. The five Aster settings omit
  their redundant explicit title rule, so the table is the sole row-title owner.
- Existing variance and missing-Actual text participates in later label placement.
  The focused generic collision test passes, and the Aster `FTL and media management`
  row no longer duplicates its title beside `+7d`.
- The Aster README documents both full SVG+PNG verification and `--no-raster` SVG-only
  regeneration with its optional runtime dependencies.
- The Controller Z executive SVG now reproduces byte-for-byte from the documented
  command; a checked-in artifact equality assertion prevents it becoming stale again.
- General Date/CalendarPeriod leap-year handling remains delegated to the calendar
  library's Gregorian target-month calculation. No year-specific branch and no new
  exhaustive leap-year fixture set were added.

## Evidence

- `python -m pytest -q`: **248 passed**; two existing non-failing
  `jsonschema.RefResolver` deprecation warnings.
- `timeline-design/docs/fixtures/run_conformance.py`: every stage passes.
- Aster SVG/PNG regeneration: five outputs, each with zero raster overflow.
- Controller Z executive and review-detail SVG/PNG verification: zero raster overflow.
- Aster overview visual inspection: table titles are singular, planned gates are white,
  and the `+7d` variance annotation is separated from the row title.
- Aster overview SVG SHA-256:
  `f1516aaac70e74b8ac5d86be59be3d6e3bb0352b7cb46a5976ebe7d320f76942`.
- Controller Z executive SVG SHA-256:
  `1afc603c347101e2167f3b79c3f7a1e44af0054654729e9fec26dc0bf32642cb`.
- Controller Z review-detail SVG SHA-256:
  `53c62daaaee3d0871f248840147f732a0d1b1a75d505e2bbfcaf1fc2d7f3a9bd`.

## Release decision

The accepted defects in #14, #16, and #17 are corrected by published generic contracts,
implementation, tests, and regenerated artifacts. Each issue received evidence linking
`d123b57` and this review's `1c84ac9` commit and was closed as completed. M23 remains
complete; this corrective program introduces no new product-feature milestone or
semantic authority.
