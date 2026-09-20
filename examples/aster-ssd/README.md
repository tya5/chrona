# ASTER Enterprise SSD sample

This is a fictional development program. Dates, observations, holidays and risks
are demonstration data, not a real product commitment or a national calendar.

## Design contract

One authoritative Project contains 24 objects across six teams and 28 dependency
edges. It combines fixed tasks, fixed gates, scheduled work, start-to-start
overlap, finish-to-start sequencing, multi-predecessor convergence, calendar-day
stress duration, two work calendars, calendar exceptions, calendar-qualified lag,
anchors and an upper-bound constraint.

Actual observations remain separate from the plan. Revised observations exercise
latest-sequence selection. Missing and unmatched observations remain explicit.
Actual dates do not reschedule the baseline or imply a forecast.

## Visual direction

Use an ink/navy background, amber plan bars and cyan observed bars. Team section
headings replace Controller Z's merged owner column. The wider work-item column,
table-owned row titles, optional timeline annotations, and sectional whitespace provide a distinct layout
without a custom renderer.

Four 1600 × 900 slides share one design: an eight-item executive selection,
platform/firmware, performance/security, and qualification/production. Three
detail slides cover every object once. A tall master view shows all objects and
all dependencies, including edges across slide boundaries. Per-slide edges only
connect selected endpoints; no invented transitive edges are drawn.

All resources use existing schemas. No new engine feature, hardcoded ASTER
renderer branch, or preset inheritance is needed. Complete settings avoid the
known unresolved preset-reference contract. This sample does not claim to close
the prior P1–P5 review findings. Partial-progress bars, actual milestone markers,
federation and interactive editing are outside this rendered sample's scope.

## Files and regeneration

`project.yaml` owns planning facts and `actual.yaml` owns observations. Each
`*-view.yaml` selects rows and its date window. Each `*-settings.yaml` contains
complete appearance settings (JSON syntax is valid YAML). Settings pin the same
Nimbus Sans font metrics as the Controller Z example. A different font install
must provide its verified hash. `profile.yaml`, `style.yaml` and `theme.yaml`
are compatibility resources for the current adapter; v0.2 settings control the
visual appearance. No preset-reference resolution is required.

```sh
.venv/bin/python scripts/render_schedule_sample.py examples/aster-ssd/manifest.yaml
.venv/bin/pytest -q tests/test_aster_sample.py
```

The default command regenerates SVG and verifies PNG output. It requires Node, `sharp`,
and `CODEX_PRIMARY_RUNTIME_NODE_MODULES` (or an equivalent `NODE_PATH`). To regenerate
and verify deterministic SVG only, without raster dependencies, run:

```sh
.venv/bin/python scripts/render_schedule_sample.py examples/aster-ssd/manifest.yaml --no-raster
```

SVG files retain text, shapes and source IDs for editing. PNGs are slide-ready
previews. The master is 1600 × 2100, deliberately not a presentation slide.
`slides.html` embeds the four slide previews for offline viewing; the SVG
resources remain the editable originals. This is not a PowerPoint deck.
White diamonds mean planned gates; this sample does not assert actual gate
completion. Missing actual is not equivalent to delay. Two unmatched observations
belong to the project-wide data set, so each view repeats the same count.

## Feature locations

| Feature | Concrete example |
| --- | --- |
| Parallel start dependency | Boot start + 3 engineering workdays starts FTL |
| Multiple prerequisites | Firmware, performance and security gates unlock integration |
| Calendar-qualified lag | Qualification gate + 1 factory workday starts pilot |
| Different calendars | Five-day engineering and six-day factory workweeks |
| Calendar exception | Factory closure on 10 July moves pilot to 12 July |
| Calendar-day duration | Endurance runs continuously for 42 days |
| Latest observation | NAND sequence 2 replaces sequence 1, giving +5 calendar days |
| Deadline constraint | Protocol interoperability must finish by 2 July |
| Multiple projections | One plan, four slide views and a complete master |

The executive selection has only one direct selected-to-selected dependency.
It is a checkpoint view, not a critical-path calculation. The master preserves
all 28 edges. Dependency crossings or shared route segments are not evidence
of an additional relationship; source IDs identify the actual edges.

## Verification

The full suite passed 175 tests. Five rendered outputs passed the existing
raster width check (56 annotated work-item lines in total), and all five PNGs
were visually inspected. Tests check schema conformance, calendar behavior,
latest observation selection, row coverage, generated SVG reproducibility and
dependency routes avoiding planned/actual bar interiors. The raster check does
not measure every SVG text node. No Chrona engine source was changed for this
sample; it uses existing scheduling, projection and rendering capabilities.
