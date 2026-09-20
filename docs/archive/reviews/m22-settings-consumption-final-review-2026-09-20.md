# M22 settings-consumption final review — 2026-09-20

**Disposition:** Pass

## Scope and sequencing

The remediation followed the published D24 plan. Product implementation began only
after the initial design checkpoint, and each newly discovered semantic boundary
stopped implementation until its addendum was documented, validated, published, and
tree-verified. M23 remained deferred.

## Acceptance evidence

- I24-1 completed Rect radius/minimum width, lane group/stack metadata, and complete
  purpose-owned stroke tokens.
- I24-2 completed variance status/marker families, Missing Actual modes and pattern,
  annotation paints, and conditional paint observers.
- I24-3 completed minor ticks, label-rule sources and requiredness, visibility gates,
  optional typography, and date labels.
- I24-4 completed explicit primitive optionality, Output precision/capability/overflow,
  and the 24-row matrix-driven closure test without a `KNOWN_INERT` allow-list.
- `python -m pytest -q`: 239 passed; two pre-existing `jsonschema.RefResolver`
  deprecation warnings remain non-failing.
- `conformance/run_conformance.py`: all suites pass, including
  `Presentation setting consumption matrix: PASS (24 rows)`.
- `tools/render_schedule_sample.py examples/aster-ssd/manifest.yaml`: all five SVG
  and PNG artifacts reproduced deterministically with zero reported overflow.
- Visual review of the integrated ASTER master confirms readable planned/Actual bars,
  status markers, Actual-date and Missing-Actual labels, connectors, table rules, and
  legend content within the declared viewport.

## Issue and pull-request disposition

Issue 11's common-Scene radius and stack-metadata defect is fixed. Issue 12's valid
conditional-consumption findings are closed by targeted fixtures; its original
single-sample inert count is not used as acceptance evidence. PR 13 is not merged
because its exact-path `KNOWN_INERT` oracle classifies absent conditional triggers as
defects. Its useful perturbation intent is superseded by the versioned matrix plus
targeted observers on `main`.

M22 is complete. No Project, Schedule, Actual, or M23 semantic authority changed.
