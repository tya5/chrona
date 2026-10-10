# chrona roadmap

Chrona's own road to a product release candidate, drawn by Chrona. Work items are
grouped into milestones M0 (reach the design targets) through M4 (more authors), then
RC (release candidate). The reviewer maintains it; dates are the reviewer's estimates.

It reuses the approved target B design from [`halcyon-1`](../halcyon-1/): the Theme,
Scheme, Layout and detail profile are copies of the target B ones, with the group tint
scale given as a palette over the milestones in display order.

| File | Holds |
|---|---|
| `project.yaml` | The current plan: work items, gates, dependencies and notes. |
| `actual.yaml` | Observed actuals and the `asOf` date. |
| `snapshots/plan-2026-10-10/project.yaml` | The 2026-10-10 plan, used as the baseline. |
| `views/roadmap.yaml` | What the slide shows. |
| `themes/`, `schemes/`, `layouts/`, `profiles/` | The target B appearance and composition. |

## Updating

1. Change plan dates (or add work items) in `project.yaml`.
2. Record actuals in `actual.yaml` from GitHub issue dates: `start` is the day work
   started or the PR was opened; `finish` is the issue's `closedAt` date.
3. Move `asOf` forward to the update date.
4. Leave `snapshots/plan-2026-10-10/` alone: the baseline stays the 2026-10-10 plan, so
   slips show against it.
5. Update the project `contentIdentity` in `contexts/roadmap.yaml` to the sha256 of the
   new `project.yaml` bytes.

The SVG and Scene under `generated/` are derived on `main`; do not edit them. To
preview locally:

```sh
PYTHONPATH=$PWD/src:$PWD python3 tools/materialize_example.py \
  examples/chrona-roadmap/manifest.yaml --slide roadmap --output /tmp/roadmap --write
```
