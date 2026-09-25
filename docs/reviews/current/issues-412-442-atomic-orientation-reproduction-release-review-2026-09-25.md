# Release Review — Atomic Orientation and Cross-Python Reproduction (#412, #442)

**Decision:** accepted for one atomic public release.

## Scope reviewed

The release combines #412's View v0.18, Layout Profile v0.8, Scene v0.5,
completed orientation geometry and adapters with #442's deterministic Layout
float accumulation, structural accumulation gate, and newest-minor CI gate.
The combination is required because immutable generated Scenes record the
changed View/Profile inputs and completed text layout alongside placement
coordinates.

## Architecture review

* View selects only finite axis-label and table-header intent; every public
  declaration is explicit.  Layout owns measurement, bounds, baseline,
  angle, fitting and overflow; Scene transports the result; adapters consume
  only supplied `rotation_degrees`.
* The Scene builder remains a projection: structural tests reject direct text
  measurement, routing, annotation placement, and axis-coordinate selection.
  SVG, Typst and TikZ tests additionally reject adapter-side orientation
  inference and text measurement.
* `geometry_sum` is Layout-only.  Decimal profile-engine sums and count sums
  remain in their native domains; direct unclassified builtin float sums in
  Layout are rejected by `check_layout_float_accumulation.py`.
* The table-header physical containment check tolerates only sub-micro-point
  binary conversion residue.  It still rejects a real escape from the reserved
  header interval with `E_LAYOUT_TABLE_OVERFLOW`.

## Evidence reviewed

* Flight-readiness intentionally contains `rotate-cw` axis labels.  Its Scene
  carries `orientation: rotate-cw`, `rotationDegrees: 90`, the Layout-computed
  occupied rectangle and baseline; its SVG has matching `rotate(90 x y)`
  transforms.
* All 21 public contexts were regenerated.  The known #442 HALCYON contexts
  (`mission-brief`, `gallery-dark`, `gallery-mono`) now reproduce with the
  same committed bytes on local Python 3.12.7 and Python 3.11.15 virtual
  environments.
* No interpreter identity, serializer rounding workaround, compatibility
  reader, or adapter numeric policy was introduced.

## Verification

* Focused presentation units cover contracts, fonts, icons, Layout, model,
  renderers, review and Scene; all passed.  Core/non-presentation unit tests
  (107) and the independently partitioned tool suites passed.  CLI: 46
  passed.  Acceptance: 155 passed, 18 skipped.  Integration: 116 passed,
  1 skipped.
* Python 3.11 and 3.12 each passed the complete public corpus materializer
  reproduction test; Python 3.11 also passed documented-command execution.
* Conformance, schema annotations, generated diagnostic/coverage checks,
  Scene delivery ownership, View dispatch reachability, import direction,
  text encoding, semantic registry reachability, semantic realization
  coverage, and diff whitespace checks passed.

## CI release gate

The retained three-OS Python 3.11 conformance job now executes the new Layout
accumulation check.  `reproduction-newest-python` on Ubuntu Python 3.12 runs
the complete public corpus materializer reproduction test.  This establishes
the lowest/newest-minor evidence invariant without multiplying wheel builds.

## Follow-up boundary

#411 remains a separate system-font policy issue.  #404 may reuse #412's
completed orientation facility only through Layout; it must not add another
transform pipeline.
