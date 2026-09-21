# HALCYON-1 smallsat mission

A fictional 26-object, 24-dependency spacecraft programme from preliminary design review to first
light, rendered three ways from one plan. Dates, observations, holidays and risks are demonstration
data.

| Slide | View | Layout | Theme / scheme | Viewport |
|---|---|---|---|---|
| `mission-brief` | gates plus the critical spans, two columns | `briefing` — title, table beside timeline, notes as a footer | `briefing` / `mission-light` | 1600 × 900 |
| `programme-board` | every object, grouped by owning team | `wallboard` — title and notes in a left sidebar | `wallboard` / `control-room-dark` | 1920 × 1080 |
| `launch-campaign` | the launch phase only, July to November | `print-portrait` — a `grid` with the title spanning both tracks | `print` / `print-mono` | 1200 × 1120 |

Each slide is a different **View × Layout × Theme × Color Scheme** binding of the same
`project.yaml` and `actual.yaml`. The three Themes declare the full v0.5 role contract — per-role
typography (`heading`, `subtitle`, `axis`, `legend`, `annotation`, `text`), the variance and
missing-Actual paints, per-team `group:<id>` category bindings, and a dependency marker — so the
example picks up richer output as the Scene runtime consumes those roles.

## What the plan exercises

- Two work calendars: `engineering` (Mon–Fri with four closures) and `range` (Mon–Sat with two
  blackout dates). `campaign` and the `shipment → campaign` lag both run on the range calendar.
- Fixed gates (`pdr`, `cdr`, `payload-delivery`, `psr`, `frr`, `launch`, `first-light`) alongside
  scheduled spans; five spans are anchored (`eps`, `optics`, `mcs`, `station`, `rehearsals`).
- Calendar-day durations for environmental testing (`payload-tvac: 8d`, `tvac: 14d`, `leop: 21d`)
  next to work-day durations.
- A three-way convergence into `integration` and into `launch`, plus an upper-bound constraint on
  `emc`.
- Observations through 20 Aug 2027 with a revised observation (`avionics` sequence 2), late and
  early finishes, and two unmatched external observations that never touch the plan.
- Three project annotations, rendered through the `notes` slot.

## Files

```
project.yaml  actual.yaml  manifest.yaml  README.md
views/  layouts/  themes/  schemes/  styles/
contexts/<slide>.yaml     generated immutable Render Context v0.5 per slide (do not hand-edit)
generated/<slide>.svg     acceptance artifact produced by chrona render-review
slides/<slide>/preview.png  raster review copy of the same SVG
```

## Regenerate

```sh
python tools/materialize_example.py examples/halcyon-1/manifest.yaml --slide mission-brief --output /tmp/halcyon/mission-brief --write
python tools/materialize_example.py examples/halcyon-1/manifest.yaml --slide mission-brief --output /tmp/halcyon/check
```

The first form rewrites `generated/01-mission-brief.svg` from `contexts/01-mission-brief.yaml`;
the second fails with `E_MATERIALIZER_MISMATCH` if the checked-in SVG differs, which is what
`tests/acceptance/examples/test_halcyon_example.py` runs for every slide. Each manifest slide
names its own `context`, so the three slides render from three independent immutable bindings.
Previews are rasterised from the generated SVG (any SVG renderer will do; `cairosvg` was used).
