# HALCYON-1 example

The **programme** register of the corpus: scale, hierarchy, comparison modes, the
second surface and extension-typed objects, on one spacecraft programme.

- `project.yaml` owns 29 objects on two calendars, three `group` objects with `rollup`
  schedules (`spacecraft-ait`, `ground-segment`, `mission-closeout`) whose children carry
  `parent` and `wbsCode`, `plannedProgress`, a `link`, a `deadline` on the pre-ship
  review, and two scenarios. `tvac-slip` changes a duration, removes a dependency and
  adds a re-wired one, and clears the deadline it would otherwise miss.
  `payload-fast-track` replaces the detector-to-payload-TVAC dependency with one
  carrying a negative lag (`-3wd`): payload TVAC starts three working days before
  detector calibration ends.
- `project.yaml` declares `extensions[0].resource`, a reference to
  `extensions/semiconductor-development.yaml`, a `chrona/profile/v0.3` package that
  defines the `PDR`, `CDR` and `PSR` review-gate profiles, the `approval` enum field they
  require, and the package-wide `model`, `customerReview` and `lot` fields. The package's
  own `contentIdentity` frames the document with that field omitted. The `pdr`, `cdr` and
  `psr` gates use the package types directly (`type: PDR`), and every work item carries
  a `model` (`EM`, `QM` or `FM`).
- `actual.yaml` records span observations, point observations for gates that were held
  (`cdr`, `payload-delivery`), an in-flight observation with partial progress, and two
  unmatched external records.
- `project.yaml` also names one period, `launch-window` (opens at the `launch` gate, closes 5 Nov 2027, exclusive end
  6 Nov). `views/02-programme-board.yaml` selects it and the `wallboard` Theme's `period-band` role paints it; the
  programme-board, overlay-briefing and glyph-gates slides share that View and show the band. The View also declares the
  derived figure `launch-countdown` (calendar days from the as-of to the start of `launch-window`); the programme board's
  `profiles/summary-countdown.yaml` shows it as the first key figure, the Title Card target's `63 DAYS` by YAML only.
- `snapshots/baseline-2027-06.yaml` is a `snapshot-ref` pinning
  `snapshots/baseline-2027-06/project.yaml`, the plan as approved in June, under its own
  revision token. `views/07-replan-baseline.yaml` compares the current plan against it
  with `comparison.baseline: snapshot`.
- `views/` hold six further Views over the same facts: an overview, a dense board with a
  colour scale and progress fill, a grouped campaign, a scenario comparison, the
  dependency-network surface, and a hierarchy-grouped readiness review with critical
  relations and float.
- `views/26-gates.yaml` shows the typed review gates on the bus and payload chain with
  `Model` and `Approval` columns, encodes `model` as a colour scale (`colorEncoding` over
  `EM`, `QM`, `FM`, slots in `schemes/gates-light.yaml`, mapping in
  `themes/gates-light.yaml`) and compares against `payload-fast-track` with
  `comparison.baseline: scenario`, so the negative lag shows as the earlier scenario bar.
  It was folded in from the retired `orion-asic` example.
- `themes/`, `schemes/` and `layouts/` supply the appearances and compositions.
- The five approved target designs, `target-b`, `yuya`, `titlecard`, `marquee` and `sunday`, are not
  copied here. They are shared designs in the packaged store (`src/chrona/resources/designs/<design>/`:
  `theme.yaml`, `scheme.yaml`, `layout.yaml`, `detail.yaml` and, for `titlecard`, `summary.yaml`). Their
  Contexts (`contexts/21-target-b.yaml` … `contexts/25-sunday.yaml`) reference them with
  `store: {provider: package, identity: chrona.resources}`, together with the packaged icon catalogs
  (`icons/chrona-*-v2026-10-09.yaml`). Only their thin Views (`views/21-target-b.yaml` …
  `views/25-sunday.yaml`) stay here, because a View is the Project's connector.
- `contexts/<slide>.yaml` are the immutable bindings; `generated/<slide>.svg` is the
  materializer evidence declared by `manifest.yaml`.
