# RC acceptance — approved designs and public slides

Observed: 2026-10-24. Product evidence is pinned to ready main
[`b49c14eb7d6dfcb29c15f1883438c11ad917ebd1`](https://github.com/tya5/chrona/commit/b49c14eb7d6dfcb29c15f1883438c11ad917ebd1),
containing PRs #1953, #1954 and #1955. Both checks below use that exact main.

Authority: [owner-approved RC criterion and assignment](https://github.com/tya5/chrona/issues/1848#issuecomment-6381296697),
[check ownership split](https://github.com/tya5/chrona/issues/1848#issuecomment-6381440472),
and [record plan / publication receipt](https://github.com/tya5/chrona/issues/1848#issuecomment-6381986028).
The criterion is: “the five approved designs (target-b, yuya, titlecard,
marquee, sunday) and HALCYON-1 do not break on the public slides or on a
standard plan.” This is an RC record, not closure of #1848 or acceptance of
all its colour-vision and design-polish work.

## Criterion parts

| Part | Result | Evidence |
| --- | --- | --- |
| Public slides: the five approved designs and HALCYON-1 do not break. | met | [RC check 1, exact-main re-run](https://github.com/tya5/chrona/issues/1848#issuecomment-6378315428): all 19 HALCYON-1 and 5 chrona-roadmap manifest contexts, completed Scene bounds against actual SVG text and bundled-font raster inspection. Text overlap/clipping, member-name loss, paired stubs, legend coverage, canvas width, render validity and warning differences are checked per slide. |
| Standard plan: the five approved designs do not break. | met | [RC check 2 re-run](https://github.com/tya5/chrona/issues/1848#issuecomment-6381636800), [reviewer acceptance](https://github.com/tya5/chrona/issues/1848#issuecomment-6381640541): trial-15 week-3, all five designs in en-US, plus yuya and titlecard in ja-JP; seven successful renders, no off-canvas or overlapping text, no paired-stub receipts, and complete legend coverage. |
| Only a finding that breaks the approved criterion enters RC; everything else waits until after RC. | met | [Reviewer disposition](https://github.com/tya5/chrona/issues/1848#issuecomment-6381640541) accepts readable direct-leader fallback and leaves the listed contrast/separability warnings after RC. No new polish issue, numerical quality threshold or product change is introduced by this review. |

The former seven unkeyed-role findings are resolved: #1954 adds the six
`calendar-closed` keys; owner-approved #1955 adds Sunday's `progressFill`
key and matching lighter tint. This does not assert that every warning is
absent. Warning changes, declared optional suppression and vertical canvas
growth are disclosed in check 1 rather than mistaken for silent loss or
width overflow. The checks add no blanket clearance or readability waiver.
The auxiliary 12-pixel leader probe in check 2 is not an RC contract; typed
route receipts and the accepted visible output are the evidence.

## Reproduction and publication gate

Public inputs: [trial-15/plan at e1c6426](https://github.com/tya5/chrona/tree/e1c6426def3d95c1873e76f54ebe8440fad8c927/trial-15/plan).
From that directory, with Chrona installed from the product evidence commit:

```sh
chrona render w3-project.yaml --preset PRESET --actual w3-actual.yaml --snapshot baseline.yaml --locale LOCALE --viewport 1600xauto --output out.svg --emit-scene out.scene.json
```

Use the preset/locale pairs in check 2. Public slide inputs and outputs are
the [HALCYON manifest](https://github.com/tya5/chrona/blob/b49c14eb7d6dfcb29c15f1883438c11ad917ebd1/examples/halcyon-1/manifest.yaml)
and [roadmap manifest](https://github.com/tya5/chrona/blob/b49c14eb7d6dfcb29c15f1883438c11ad917ebd1/examples/chrona-roadmap/manifest.yaml).
No private checkout, scratch path or unpublished input is required.

The product snapshot passed [trusted gate 40074604087](https://github.com/tya5/chrona/actions/runs/40074604087).
Its [source three-OS run](https://github.com/tya5/chrona/actions/runs/40075093277)
is separate from this record's publication gate. **Release acceptance takes
effect only when the [publication receipt](https://github.com/tya5/chrona/issues/1848#issuecomment-6381986028)
cites a successful full three-OS run on the exact published main containing
this record**, including pytest, conformance, executed wheel/smoke checks,
MCP floor and newest-Python public materializers. An earlier source run or
green PR alone is not a substitute. The receipt binds the final PR/main/run
without requiring a self-referential follow-up commit.

Architecture: declarations own design intent; Layout owns completed geometry;
Scene and adapters project it. This publication changes documentation only:
no schema, core policy, project data, design YAML or derived output changes.
