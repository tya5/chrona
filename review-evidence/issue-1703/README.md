# Issue 1703 — final native trial evidence

Reference-only branch: do not merge it into `main`.
Rendered from published ready main `9e59e3f024171811d45b0f6b7b1f6c89f1587754`.
Inputs are unchanged [trial-6 files at 531f5007e](https://github.com/tya5/chrona/tree/531f5007e26927fb2c25880aefb0af4389444a76/trial-6).
No Project, View or Theme adaptation was made for these renders.

Run from that input directory with Chrona installed from the source commit:

```sh
chrona render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --preset target-b --output compare-targetb.png --emit-scene compare-targetb.scene.json
chrona render plan.yaml --actual actual-week2.yaml --snapshot baseline.yaml --forecast --preset technical-print --view tp-deadlines-view.yaml --output forecast-tp-deadlines.png --emit-scene forecast-tp-deadlines.scene.json
chrona render starter/project.yaml --actual starter/actual.yaml --output starter.png --emit-scene starter.scene.json
```

Before/after counts use the published pre-change main `5fe41db8e` and the final
source above. The final PNGs are byte-identical to the candidate already
personally inspected in the [literal review](https://github.com/tya5/chrona/blob/9e59e3f024171811d45b0f6b7b1f6c89f1587754/docs/reviews/current/issue-1703-legend-acceptance-review-2026-10-18.md).
Their Scenes retain the same primitive and diagnostic counts.

| Case | Primitives before → after | Added / removed / changed | Diagnostics before → after | Result |
| --- | ---: | ---: | ---: | --- |
| `compare-targetb` | 304 → 304 | 0 / 0 / 32 | 29 → 30 | Faithful black Actual/Gate keys; one pointed swatch-collision warning. Thirty Task path labels and two inline rounding changes account for the changed primitives. |
| `forecast-tp-deadlines` | 299 → 303 | 4 / 0 / 0 | 29 → 29 | Baseline and Deadline swatch/label pairs added. |
| `starter` | 68 → 68 | 0 / 0 / 0 | 2 → 2 | One ACTUAL key, no duplicate-label warning. |

The PNG/Scene pairs are evidence, not compatibility or byte-identity targets.
The native three-OS release gate is tracked separately on the issue.
