# Executive summary native evidence — issue1700

Reference-only evidence branch; do not merge it. After source:
`f172dfb0be65fd01d650bd166b3e85e2cb761d08`. Before renderer:
`fa106a308f134ed5bcdc269108890dac18a80d7d` (runtime/resources identical to
ready main `331a05496a47d1a5243fd9e978be91607f3212e3`; its difference is a test repair).
Both runs use these identical CSV-imported Project/View inputs and, for
mission-light, the same local Layout with `rowDistribution: fill`.
No shipped preset or Project data was adapted between runs.

| Preset | Primitives before → after | Added / removed / changed | Text before → after | Retained gates before → after | Duplicate overlays before → after | Routes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| default | rejected → 42 | n/a | rejected → 15 | rejected → 2 | rejected → 0 | 0 |
| executive-light | 39 → 40 | 4 / 3 / 27 | 12 → 14 | 0 → 2 | 3 → 0 | 0 → 0 |
| mission-light | 37 → 38 | 4 / 3 / 27 | 11 → 13 | 0 → 2 | 3 → 0 | 0 → 0 |

Default previously rejected `summary-bar/markHeight` with
`E_THEME_ROLE_REQUIRED`, so there is no before PNG. The only removed IDs are
`summary-bar:programme`, `summary-bar:design`, `summary-bar:delivery`.
The four added primitives are the two gates and their two names. Existing
marks/text move because retained dates extend the selected window and ordinary
member tracks close in their retained rows. Every successful after run has
exactly three primary summary marks, two gates, and both full gate captions.
The five PNGs were visually inspected, not inferred from Scene counts.

After default reports the existing `W_LAYOUT_AXIS_LABEL_THINNED` and
`W_LAYOUT_AXIS_DENSITY` for the short final March bucket; January/February and
both gates remain visible. The other two after renders have no warnings.
All runs also report the existing relation-routing/policy info messages.
No selected-gate or member-label suppression is accepted here.

Run the [executable guide](../../docs/guides/executive-summary.md) to create
the inputs, then use each renderer checkout's own venv:

```sh
chrona render executive-project.yaml --view executive-view.yaml --output after-default.png --emit-scene after-default.scene.json
chrona render executive-project.yaml --view executive-view.yaml --preset executive-light --output after-executive-light.png --emit-scene after-executive-light.scene.json
chrona render executive-project.yaml --view executive-view.yaml --preset mission-light --layout mission-light-layout.yaml --viewport 1600x900 --output after-mission-light.png --emit-scene after-mission-light.scene.json
```

The same commands with `before-` output names were used on the before renderer.
This evidence is not the official public-materializer snapshot or the required
exact-main three-OS release gate.
