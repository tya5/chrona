# HALCYON-1 smallsat mission

A fictional 26-object, 24-dependency spacecraft programme from preliminary design review to first
light, rendered three ways from one plan. Dates, observations, holidays and risks are demonstration
data.

| Slide | View | Layout | Scheme | Viewport |
|---|---|---|---|---|
| `01-mission-brief` | gates plus the critical spans, two columns | `briefing` — title, table beside timeline, notes as a footer | `mission-light` | 1600 × 900 |
| `02-programme-board` | every object, grouped by owning team, three columns | `wallboard` — title and notes in a left sidebar | `control-room-dark` | 1920 × 1080 |
| `03-launch-campaign` | the launch phase only, window derived from the selection | `print-portrait` — a `grid` with the title spanning both tracks | `print-mono` | 1200 × 1120 |

Each slide is a different **View × Layout × Theme × Color Scheme** binding of the same
`project.yaml` and `actual.yaml`; no slide carries a coordinate, a colour literal outside its
scheme, or a copy of a project fact.

## What the plan exercises

- Two work calendars: `engineering` (Mon–Fri with four closures) and `range` (Mon–Sat with two
  blackout dates). `campaign` and the `shipment → campaign` lag both run on the range calendar.
- Fixed gates (`pdr`, `cdr`, `payload-delivery`, `psr`, `frr`, `launch`, `first-light`) alongside
  scheduled spans; four spans are anchored (`eps`, `optics`, `mcs`, `station`, `rehearsals`).
- Calendar-day durations for environmental testing (`payload-tvac: 8d`, `tvac: 14d`, `leop: 21d`)
  next to work-day durations.
- A three-way convergence into `integration` (bus test, payload delivery) and into `launch`
  (flight readiness review, operations rehearsals), plus an upper-bound constraint on `emc`.
- Observations through 20 Aug 2027 with a revised observation (`avionics` sequence 2), one span
  that finished late (`payload-tvac`) and one that finished early (`station`), and two unmatched
  external observations that never touch the plan.
- Three project annotations, rendered through the `notes` slot.

## Files

```
project.yaml    actual.yaml    manifest.yaml    gallery.html
views/          layouts/       themes/          schemes/        styles/
contexts/       generated immutable Render Context per slide (do not edit)
slides/<name>/  expected.svg (acceptance artifact) and preview.png (raster review copy)
```

## Regenerate

```sh
python tools/materialize_example.py examples/halcyon-1/manifest.yaml             # write SVG + contexts + gallery
python tools/materialize_example.py examples/halcyon-1/manifest.yaml --previews  # also rasterize preview.png (needs cairosvg)
python tools/materialize_example.py examples/halcyon-1/manifest.yaml --check     # verify, as the acceptance test does
```

The materializer copies each authoring resource byte-for-byte into a temporary local snapshot
store, generates a `chrona/presentation/v0.5` Render Context with SHA-256 references, records it
under `contexts/`, and calls `chrona render-review`. `preview.png` files are review copies, not
acceptance artifacts; only `expected.svg`, `contexts/` and `gallery.html` are byte-checked.
