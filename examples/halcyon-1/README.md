# HALCYON-1 example

The **programme** register of the corpus: scale, hierarchy, comparison modes and the
second surface, on one spacecraft programme.

- `project.yaml` owns 29 objects on two calendars, three `group` objects with `rollup`
  schedules (`spacecraft-ait`, `ground-segment`, `mission-closeout`) whose children carry
  `parent` and `wbsCode`, `plannedProgress`, a `link`, a `deadline` on the pre-ship
  review, and one scenario. The scenario changes a duration, removes a dependency and
  adds a re-wired one, and clears the deadline it would otherwise miss.
- `actual.yaml` records span observations, point observations for gates that were held
  (`cdr`, `payload-delivery`), an in-flight observation with partial progress, and two
  unmatched external records.
- `project.yaml` also names one period, `launch-window` (opens at the `launch` gate, closes 5 Nov 2027, exclusive end
  6 Nov). `views/02-programme-board.yaml` selects it and the `wallboard` Theme's `period-band` role paints it; the
  programme-board, overlay-briefing and glyph-gates slides share that View and show the band.
- `snapshots/baseline-2027-06.yaml` is a `snapshot-ref` pinning
  `snapshots/baseline-2027-06/project.yaml`, the plan as approved in June, under its own
  revision token. `views/07-replan-baseline.yaml` compares the current plan against it
  with `comparison.baseline: snapshot`.
- `views/` hold six further Views over the same facts: an overview, a dense board with a
  colour scale and progress fill, a grouped campaign, a scenario comparison, the
  dependency-network surface, and a hierarchy-grouped readiness review with critical
  relations and float.
- `themes/`, `schemes/` and `layouts/` supply three appearances and four compositions.
- `contexts/<slide>.yaml` are the immutable bindings; `generated/<slide>.svg` is the
  materializer evidence declared by `manifest.yaml`.
