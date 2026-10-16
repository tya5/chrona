<!-- chrona:literal-acceptance/v1 -->

# Sunday snapshot profile acceptance

Implementation: `5b775d75c`, ready base `bb28a288b`, [PR1601](https://github.com/tya5/chrona/pull/1601).
Final-head [CI38927819993](https://github.com/tya5/chrona/actions/runs/38927819993)
and exact review-containing main `69a5a5ede2a15b68a4a606345493c22b2d597ad2`
[three-OS release38930033890](https://github.com/tya5/chrona/actions/runs/38930033890)
passed; the issue is closed.

## Literal issue acceptance

### Issue #1594

- Source: [Issue #1594](https://github.com/tya5/chrona/issues/1594)
- Observed: 2026-10-17

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | The test above passes for all 15 presets (or names each preset that cannot draw a baseline, with the refusal being a clear warning, not an error). | met | [Snapshot matrix](../../../tests/unit/chrona/usecases/test_draft_snapshot.py): all library IDs, both SVG/PNG, Actual and changed Snapshot, no profile flag; artifact signatures, consumed inputs, ghosts or explicit `W_SNAPSHOT_NOT_DRAWN`, and input immutability. Related snapshot/draft/CLI batch: 96 passed in28.52s. | — |
| 2 | The command above on `examples/chrona-roadmap` renders, viewed as PNG. | met | Root ran `.venv/bin/chrona render examples/chrona-roadmap/project.yaml --preset sunday --snapshot examples/chrona-roadmap/snapshots/plan-2026-10-10/project.yaml --actual examples/chrona-roadmap/actual.yaml --output /private/tmp/chrona-1594-roadmap.leAuZ7/sunday.png` and viewed the PNG from the [committed project](../../../examples/chrona-roadmap/project.yaml): chart, Actual marks and changed baseline ghosts present. No visual-capability error; existing contrast warnings remain explicit. | — |
| 3 | Public SVG/Scene byte-identical. | met | [Final BOT artifact12057377678](https://github.com/tya5/chrona/actions/runs/38927819993/artifacts/12057377678), sourcec73890637 against ready66bf64325: all109 before/after paths byte-identical, including50 SVG +50 Scene;0 added/retired. No corpus or generated-output edits. | — |

## Programme-level criteria (optional)

Only Sunday's library entry declares the existing v0.7 family preference.
Existing target-peer negotiation selects SVG/PNG. Core, Layout geometry, Scene,
adapters and schema contracts are unchanged; no preset-specific renderer branch.
