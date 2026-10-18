# Issue 1680 — forecast deadline acceptance

<!-- chrona:literal-acceptance/v1 -->

Implementation: `42e25bd10`; native regression publication: `82f96bdc5`.
[Current plan/design](../../planning/active/issue-1680-forecast-deadline-work-record-2026-10-18.md).
Merged [PR1689](https://github.com/tya5/chrona/pull/1689) at `82c1e96b6`;
head `955190f29` passed [CI39084366543](https://github.com/tya5/chrona/actions/runs/39084366543).
Trusted main `53f83ad721549ed6ab023b3d45a07a19b5285e1d` passed the full three-OS,
wheel/smoke and newest-Python reproduction gates in
[release39085607822](https://github.com/tya5/chrona/actions/runs/39085607822).
The official PR artifact preserves all50 SVG/Scene pairs; only diagnostic
inventory source coordinates change. Keep the issue open until the release
gate on the main commit containing this final review also succeeds.

## Literal issue acceptance

### Issue #1680

- Source: [Issue #1680](https://github.com/tya5/chrona/issues/1680)
- Observed: 2026-10-18

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | A synthetic forecast whose finish passes the deadline draws a run to the forecast finish and emits `W_DEADLINE` naming the forecast. A forecast that keeps the deadline draws only the tick. | met | [Native SVG tests](../../../tests/integration/test_forecast_deadlines.py): ordinary/folded point/span runs end at Jan15, warnings name forecast and agree on3 days; equal/kept cases have ticks only. The late case fails against the pre-fix published wheel (no runs). | — |
| 2 | Without `--forecast`, output is unchanged (count table). | met | [Public materializer check](../../../tools/regenerate_public_examples.py) with `--check --jobs 4`: PASS, all50 public SVG/Scene pairs unchanged. Native omitted/false tests preserve Scene/SVG and legacy warning payloads. Count table below. | — |
| 3 | The trial-5 command above shows the two late runs in PNG. | met | [PNG command, counts and hash](issue-1680-forecast-deadline-acceptance-review-2026-10-18.md#output-counts-and-png-evidence): actual PNG inspected from pinned trial inputs `9fa6062de` and implementation `42e25bd10`. Beta/Public launch both draw their red late runs;31/17 exact stroke-colour pixels respectively in the run strips. | — |

## Programme-level criteria (optional)

### Output counts and PNG evidence

| Input | Added primitives | Removed | Changed existing | Routes/labels changed | New diagnostics |
| --- | ---: | ---: | ---: | ---: | --- |
| All50 public slides (no forecast) | 0 | 0 | 0 | 0 | 0 |
| Pinned trial5 forecast versus pre-fix Scene | 2 deadline runs | 0 | 0 | 0 | 2 `W_DEADLINE` |

Trial5 has2 ticks before/after and0→2 runs. All pre-existing primitive records
are identical; other trial warnings belong to the existing adjacent issues.
From the [pinned trial root](https://github.com/tya5/chrona/tree/9fa6062de/trial-5):

```sh
chrona render trial-5/plan/current.yaml --actual trial-5/plan/actual.yaml --snapshot trial-5/plan/baseline.yaml --forecast --preset trial-5/looks/tbk/preset.yaml --output /tmp/issue-1680.png --emit-scene /tmp/issue-1680.scene.json
```

Inspected local PNG (1600×855) SHA-256:
`89bd730f90ae0c0f01073ce198d0541160605448e830906ec9b800940ec7733d`.
The after Scene hash is `b598085cc1758793c9baed5ef742b8d556b40a808f27f5ce63ee11e18347e0c8`.
These are local inspection evidence, not a claimed CI artifact or release gate.

### Architecture and release

One ordered Core status tuple feeds warnings and shown deadlines. Projection
only selects eligible source facts; Layout reuses completed geometry; Theme,
Scene and adapters acquire no date comparison or new estimated paint policy.
Focused58/37 batches and7 native cases pass, including hidden/out-of-window
marks with forecast warnings. Independent review found no contract defect;
inward-import and reachability gates pass. No source-YAML or generated file
was changed. Final review-publication release remains the closing gate.
