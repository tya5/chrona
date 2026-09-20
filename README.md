# Chrona

**Chrona** is a Git-friendly grammar for temporal project data, scheduling, and
visualization.  Its source of truth is semantic, structured data; a renderer is
a consumer, never the editor-owned authority.

This repository contains the living, versioned Chrona specification and reference
implementations for the accepted delivery milestones. Core v0.1 remains the stable
Date-only scheduling profile; successor DateTime, capacity, collaboration, and
presentation capabilities are opt-in versioned profiles rather than changes to
Date-only meaning.

![Presentation slide rendered by Chrona: a 1600x900 dark Gantt showing the ASTER
qualification and production phase, with baseline and observed bars, finish
variance markers, gates and routed dependencies](examples/aster-ssd/slides/04-qualification-production/preview.png)

<sup>One of five slides in [`examples/aster-ssd`](examples/aster-ssd), rendered
from YAML with no per-sample renderer code. The chart is a derived artifact:
edit the project, re-run, and the slide follows.</sup>

## What is usable today

- deterministic Date / CalendarPeriod / WorkPeriod arithmetic;
- project JSON-Schema validation plus Core v0.1 semantic validation;
- endpoint-based dependency lower bounds and Date-only scheduled-span placement;
- executable conformance checks for the canonical Core v0.1 fixture;
- deterministic Plan/Actual review SVGs with YAML-controlled legend, group detail,
  source-labelled observations, and milestone digests.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest
chrona validate path/to/project.yaml
chrona schedule path/to/project.yaml
chrona render path/to/project.yaml --output timeline.svg
```

`validate`, `schedule`, and `render` also accept an immutable local snapshot instead of
a raw Draft path:

```bash
chrona schedule \
  --snapshot-reference project-reference.yaml \
  --snapshot-root .chrona/snapshots \
  --store-identity local-workspace
```

Use `chrona render --presentation-settings settings.yaml` for the common v0.2 Scene
path. Omitting settings intentionally selects the diagnostic legacy adapter.

`chrona render-review` accepts `--detail-profile` together with v0.2 presentation
settings. The checked-in Controller Z detail resources demonstrate the complete M23
path and produce `examples/controller-z/variants/review-detail/expected.svg`.

`chrona schedule` is a reference implementation for the acyclic Date-only
subset. It reports diagnostics for unsupported cycles rather than treating all
cycles as semantic errors.

`chrona render` is the first derived presentation slice: it projects the
resolved placements into a deterministic SVG timeline. SVG coordinates are not
project data and are never used to schedule or validate a project.

Try the included controller example:

```bash
chrona render conformance/controller-x.yaml --output controller-x.svg
```

The checked-in [controller timeline SVG](conformance/controller-x.svg)
is generated from [`controller-x.yaml`](conformance/controller-x.yaml).

For a broader semiconductor bring-up example with fixed and scheduled spans, working-day
exceptions, endpoint dependencies, parallel qualification work, gates, entities, and
annotations, render:

```bash
chrona render examples/controller-z/project.yaml --output controller-z.svg
```

## Presentation slides

A Plan/Actual review surface is rendered with `chrona render-review`, which takes
the project plus the resources that describe the presentation — what to select,
how to style it, and how to lay it out:

```bash
chrona render-review examples/controller-z/project.yaml \
  --actual  examples/controller-z/actual.yaml \
  --view    examples/controller-z/shared/view.yaml \
  --style   examples/controller-z/shared/style.yaml \
  --theme   examples/controller-z/shared/theme.yaml \
  --profile examples/controller-z/shared/layout.yaml \
  --presentation-settings examples/controller-z/variants/editorial/settings.yaml \
  --output  executive.svg
```

Appearance lives in those documents, not in renderer code, so a different look is
a different settings file against the same project.

To build a deck rather than a single chart, describe the slides in a manifest and
render them together:

```bash
python tools/render_schedule_sample.py examples/aster-ssd/manifest.yaml --no-raster
```

The manifest names the shared project, actual, style, theme and profile, then one
entry per slide giving its view, its settings and its output path. The schedule is
solved **once** and reused for every slide, so dates cannot drift between them.
Slides that are 16:9 are also collected into a single `slides.html` gallery, which
prints one slide per page.

[`examples/aster-ssd`](examples/aster-ssd) is the worked example: a 24-object,
28-dependency program across two work calendars, projected into four 1600x900
slides plus a tall master view. Drop `--no-raster` to also write PNG previews;
that path additionally requires node with `sharp`.

## Specification

The current specification set is maintained in [`docs/specification/`](docs/specification/).
Public schemas live in [`schemas/`](schemas/) and executable compatibility fixtures in
[`conformance/`](conformance/). Git history and versioned manifests preserve earlier
candidates. Start with:

1. [`docs/specification/00-vision.md`](docs/specification/00-vision.md)
2. [`docs/specification/03-temporal-model.md`](docs/specification/03-temporal-model.md)
3. [`docs/specification/04-scheduling-model.md`](docs/specification/04-scheduling-model.md)
4. [`docs/specification/05-project-format.md`](docs/specification/05-project-format.md)
5. [`docs/specification/17-implementation-delivery-profile.md`](docs/specification/17-implementation-delivery-profile.md)

Core v0.1 is Stable. Implementation discoveries are recorded through diagnostics,
ADRs, and design-first remediation before implementation changes.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for the design-first workflow and verification
requirements, [SECURITY.md](SECURITY.md) for private vulnerability reporting, and
[CHANGELOG.md](CHANGELOG.md) for notable changes.

## License

No license has been selected yet.  Do not treat this project as licensed for
reuse until a `LICENSE` file is added.
