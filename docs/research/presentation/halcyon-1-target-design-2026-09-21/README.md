# HALCYON-1 target slides — generator

`render_mocks.py` draws the hand-drawn target renderings beside this README:
three layout proposals (`board`, `sidebar`, `dossier`) x three views (`01-mission-brief`,
`02-programme-board`, `03-launch-campaign`). They are **not** renderer output; they are the
picture issues #41, #42 and #46 aim at, drawn from the `examples/halcyon-1` dataset
(scheduler placements for the plan, `actual.yaml` observations through its `asOf` date of
2027-08-20, and an illustrative baseline that the example does not yet carry).

The committed `board/`, `sidebar/` and `dossier/` directories each contain
the SVG source and PNG render for all three views. [Target B](board/02-programme-board.png)
is the approved light programme-board yardstick used by #453. These are
research references, not Chrona-generated examples or materializer output.

```sh
python docs/research/presentation/halcyon-1-target-design-2026-09-21/render_mocks.py /tmp/halcyon-mocks
# rasterise the resulting SVGs with CairoSVG at scale 1.5 to inspect PNGs
```

Compare against `examples/halcyon-1/generated/*.svg`, which is what `chrona render-review`
produces from the same project today.

| Element of the mock | Issue |
|---|---|
| Baseline ghost (dashed outline) + current plan (fill) + actual (thin dark bar) on one row | #42 section 1, #41 section 4 |
| Group header named once — band (`board`), rule (`sidebar`), tinted strip (`dossier`) | #42 section 2 |
| Quarter band over short month labels; weekend stripes, calendar exceptions, launch-window band | #42 section 3 |
| As-of line at the Actual set's cutoff | #42 section 3 |
| Delta-finish per row; hatched bar for in-progress work with no observation | #42 section 6 |
| Callouts: rail beside the timeline (`board`), numbered sidebar notes (`sidebar`), circled footnotes (`dossier`) | #41 section 5, #42 section 5 |
| Legend with swatches drawn from the same roles as the marks | #42 section 4 |

| Proposal | Idea | Scheme | Canvas |
|---|---|---|---|
| `board/` | table (work package, delta finish) beside the timeline, callout rail on the right | `mission-light` | 1600 x 900 |
| `sidebar/` | no table: labels on the plot; title, key figures and numbered notes in a left sidebar | `control-room-dark` | 1920 x 1080 |
| `dossier/` | print dossier: numbered rows with plan / actual / delta columns, outlined plan bars | `print-mono` | 1200 x 1120 |
