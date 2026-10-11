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

Current trusted READY9ea350d5 (derived-main38118112401) adopted by ordinary merge. Explicit-window Scene/SVG, paint clips, typed lane absences, window mode, date display, default axis and merged legend-grid integration:76 passed (34.01s). Import11 packages37 inward edges;224 reachable modules/no orphan;live schema annotations pass. Authored examples diff remains empty.

Current schema gate against READY9ea350d5:Scene six declared deltas,37 equal schemas,482 documents739 probes,four known-invalid unchanged. Sole failure:L2+L3=70.6s exceeds the unchanged60s budget; not accepted as green. CI must pass the same strict gate before release; cause of this timing excess is not established by semantic equivalence. Schema tooling proved/retired two merged #1293 delta entries without refreshing baseline verdicts. Previous public audit:45 unchanged;baseline-ghosts intentionally clips one snapshot/adds seven relation paint clips and an outside-window warning. That older audit is not current-head proof; inspect the new CI snapshot as one batch.

## Architecture conclusion

Layout owns window visibility, original-source absences, completed contours and clips. Scene projects typed facts and validates paint-relative containment, never repairs geometry or routes. Lane accounting uses typed ownership, not primitive-ID prefixes or project exceptions. Specs06/07/38/46/50 are normative; all literal rows above are met locally, but current-head artifact/CI and acceptance-containing exact-main three-OS release remain required. Issue stays open.
