<!-- chrona:literal-acceptance/v1 -->

# Explicit-window acceptance (#1292)

Implementation: `b599e66b`. [Current design, architecture and implementation record](https://github.com/tya5/chrona/issues/1292#issuecomment-6094241244). Authority: Specs06/07/38/46/50; paint-dependent validation correction `bf8a93b9` and host projection `d336ad2e`.

## Literal issue acceptance

### Issue #1292

- Source: [Issue #1292](https://github.com/tya5/chrona/issues/1292)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A test with an explicit window and objects before, across, and after it. From the Scene, every plot-mark primitive lies inside the plot rectangle. The canvas width equals the viewport inline size. The warning names exactly the clipped/omitted objects. | met | [Production Scene/SVG tests](../../../tests/integration/test_explicit_window_render.py): automatic and lane rows, exact source set, viewport canvas, cut outlines, closed/open actual and progress, relation endpoint suppression/contained geometry, all-omitted rows. | — |
| 2 | A window that contains every object yields no such warning, and its Scene is unchanged. | met | [Containing-window tests](../../../tests/integration/test_explicit_window_render.py) compare the entire Scene surface and SVG bytes with the derived-window render, and reject an outside-window warning. | — |
| 3 | Do not edit `examples/**`. | met | [Implementation](https://github.com/tya5/chrona/commit/b599e66b): `git diff --name-only 6c18b9e1...b599e66b -- examples` is empty. Adopted main's bot-generated evidence is not an authored change. | — |

## Programme-level criteria (optional)

Pending: final READY-base adoption, public artifact review and exact-main three-OS release CI. These local rows do not authorize closure.

Final disjoint focused batches: 109 passed (18.21s; production/builder/typed and raw clip validation/SVG-PNG containment), 111 passed (2.51s; lane/pattern/stroke adapters). Import direction: 11 packages, 37 edges, all inward. Schema-equivalence against `6c18b9e1`: PASS (Scene six exact deltas, 37 equal; 482 documents/739 probes; four known-invalid fixtures unchanged).

Layout owns visibility, original endpoints, completed contours and clip bounds. Scene copies these facts and typed absence identities; only stroke-relative terminal validation waits for paint binding, then typed and raw Scene enforce full containment. Physical-unit terminals still validate before paint. No routing, text measurement, date selection or geometry repair was added to Scene/adapters.

Public audit found four lane renders wrongly including an unowned legend mark
in the final lane inventory. Pre-code Spec50 clarification `0504c7a7` and
implementation `091baff1` restrict that account by typed ownership, never ID
prefixes. Synthetic regression and explicit-window batches: 53 passed (9.73s),
including partial owner, stripped owner and duplicate/missing rejection.
The four affected materializers are being rechecked; acceptance remains pending.
