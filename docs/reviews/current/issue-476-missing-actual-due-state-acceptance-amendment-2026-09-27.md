<!-- chrona:literal-acceptance/v1 -->

# Acceptance Amendment — Due-State Missing Actual (#476)

**Predecessor:** [original acceptance review](issue-476-missing-actual-due-state-acceptance-review-2026-09-26.md).
**Authority:** the [amended issue body](https://github.com/tya5/chrona/issues/476)
and the [owner's post-review](https://github.com/tya5/chrona/issues/476#issuecomment-5846323124).
**Published implementation:** `8153f7296daecd94f71a6a66aee10f2017e1ada2`;
derived evidence correction: `44b5604e16bd7fa2c1c3e4728a577fcbb4e200d0`.
This amendment changes the acceptance disposition, not product behavior or
the normative due-state design.

The owner corrected the original criterion 2: the shipped `tvac-in-progress`
observation makes TVAC **observed but incomplete**, not unobserved. The
inclusive due-day boundary is instead tested with a copy of HALCYON Actual
that omits that one observation. The implementation and review already used
that exact fixture. The previous `deferred` result therefore no longer
applies to the amended criterion.

## Literal issue acceptance

### Issue #476

- Source: [Issue #476](https://github.com/tya5/chrona/issues/476)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On HALCYON-1 at as-of 2027-08-20, items planned to finish after 2027-08-20 carry no missing-actual mark. | met | [HALCYON Scene/SVG integration test](../../../tests/integration/test_render.py) checks future marks absent; the [public programme-board Scene](../../../examples/halcyon-1/generated/02-programme-board.scene.json) and raster review are recorded in the predecessor. | — |
| 2 | Items due on or before as-of with no observation still carry it. The boundary case is an item planned to finish **on** the as-of date with no observation. A test covers it, e.g. with a copy of HALCYON-1's Actual set without `tvac-in-progress`. *(Amended: the shipped data has `tvac` observed and in progress, `start: 2027-08-09, progress: 0.5`, so in the shipped set TVAC is correctly not missing; the original wording wrongly said "no observation".)* | met | [Boundary integration test](../../../tests/integration/test_render.py) removes only `tvac-in-progress` from a test Actual copy, checks the due-day missing mark in Scene **and SVG**, and verifies shipped TVAC remains `Recorded` with `W_LAYOUT_ACTUAL_INCOMPLETE:tvac`. [Owner post-review](https://github.com/tya5/chrona/issues/476#issuecomment-5846323124) confirms the amended row is met. | — |
| 3 | The `missingActual` table cell follows the same rule. | met | The same [integration test](../../../tests/integration/test_render.py) asserts shipped TVAC `Recorded`, unobserved due-day TVAC `Missing`, and future items `—`; [table-state unit tests](../../../tests/unit/chrona/presentation/model/test_surface_content.py) cover the state model. | — |

## Programme-level criteria (optional)

None; this amendment changes only Issue #476's literal disposition.

## Release and architecture disposition

[CI run 36236959373](https://github.com/tya5/chrona/actions/runs/36236959373)
passed three-OS conformance, full pytest and wheel/smoke, plus newest-Python
public reproduction. The original review records focused tests, all 21 public
materializers, generated diffs and representative raster inspection. The
owner's later post-review examined committed Scenes and found only `pdr` and
`launch-contract` missing-actual marks, with no future or observed-Tvac mark.

The single View-owned `ObservationState` still feeds Layout marks, table cells
and summaries; Scene and adapters only project completed output. No layer,
schema, resource or compatibility decision changes here. All three **current
literal** criteria are met. #476 is eligible for closure after this amendment
is published and its remote commit is verified.
