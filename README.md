# Chrona

**Chrona** turns a YAML project file into a presentation-grade Gantt slide.
Define the plan, pick a presentation, render SVG or PNG. Dependencies and
working calendars decide the dates, and the data decides the layout, so the
chart is never drawn by hand.

The plan stays the source of truth. A renderer consumes it and never owns it,
so any slide can be regenerated from the data that produced it.

This repository contains the living, versioned Chrona specification and reference
implementations for the accepted delivery milestones. Core v0.1 remains the stable
Date-only scheduling profile; successor DateTime, capacity, collaboration, and
presentation capabilities are opt-in versioned profiles rather than changes to
Date-only meaning.

![Presentation slide rendered by Chrona: a 1600x900 ASTER plan-only schedule
with calendar-aware spans, gates, milestone markers and routed dependencies](examples/aster-ssd/generated/overview.svg)

<sup>Manifest-declared materializer evidence from [`examples/aster-ssd`](examples/aster-ssd).
Edit the project, re-run the materializer, and this SVG follows.</sup>

## What is usable today

- deterministic Date / CalendarPeriod / WorkPeriod arithmetic;
- project JSON-Schema validation plus Core v0.1 semantic validation;
- endpoint-based dependency lower bounds and Date-only scheduled-span placement;
- executable conformance checks for the canonical Core v0.1 fixture;
- deterministic Plan/Actual review SVGs with YAML-controlled legend, group detail,
  source-labelled observations, and milestone digests.

## Quick start

<!-- chrona:doc-check skip: requires an author-provided Project path -->
```bash
python -m pip install -e '.[dev,render]'
pytest
chrona validate path/to/project.yaml
chrona schedule path/to/project.yaml
python -m chrona validate path/to/project.yaml
```

For a Draft surface whose row count should determine its block extent, use
`chrona render --viewport 1600xauto`. This is Draft-only; immutable Render
Contexts keep a finite `environment.viewport.blockSize`.

On Windows, `python -m chrona` is equivalent to the installed `chrona` command
and avoids depending on the virtual environment's `Scripts` directory being on
`PATH`. Contributors should retain the repository's `.gitattributes`; it pins
LF checkout bytes for identity-bound YAML, JSON, SVG, and schema resources.

`validate` and `schedule` also accept an immutable local snapshot instead of a
raw Draft path:

<!-- chrona:doc-check skip: requires an author-created immutable snapshot reference and local store -->
```bash
chrona schedule \
  --snapshot-reference project-reference.yaml \
  --snapshot-root .chrona/snapshots \
  --store-identity local-workspace
```

`chrona render-review` consumes only an immutable Render Context v0.8 reference. Theme,
Layout, View, optional detail/summary inputs, viewport and Font Metrics are closed by that
Context before layout or Scene construction.

`chrona schedule` is a reference implementation for the acyclic Date-only
subset. It reports diagnostics for unsupported cycles rather than treating all
cycles as semantic errors.

`chrona render` is the first derived presentation slice: it projects the
resolved placements into a deterministic SVG timeline. SVG coordinates are not
project data and are never used to schedule or validate a project.

Try the included plan-only controller example. `render` deliberately requires
every presentation input explicitly; omit `--actual` because this View declares
it optional:

```bash
chrona render examples/controller-z/project.yaml \
  --view examples/controller-z/views/plan-only.yaml \
  --theme examples/controller-z/themes/executive-light.yaml \
  --scheme examples/controller-z/schemes/executive-light.yaml \
  --layout examples/controller-z/layouts/executive-review.yaml \
  --output controller-z-plan.svg
```

For a broader semiconductor bring-up example with fixed and scheduled spans, working-day
exceptions, endpoint dependencies, parallel qualification work, gates, entities,
annotations, and observations, add the executive View and Actual Set:

```bash
chrona render examples/controller-z/project.yaml \
  --view examples/controller-z/views/executive.yaml \
  --theme examples/controller-z/themes/executive-light.yaml \
  --scheme examples/controller-z/schemes/executive-light.yaml \
  --layout examples/controller-z/layouts/executive-review.yaml \
  --actual examples/controller-z/actual.yaml \
  --output controller-z.svg
```

## Presentation slides

A Plan/Actual review surface is rendered from a materialized v0.8 Context:

<!-- chrona:doc-check skip: requires an author-created immutable Render Context reference and local store -->
```bash
chrona render-review \
  --context-reference context-reference.yaml \
  --snapshot-root .chrona/snapshots \
  --store-identity local-workspace \
  --output executive.svg
```

Reusable authoring files live under `views/`, `themes/`, `layouts/`, and optional
`profiles/`. A different Theme changes concrete visual tokens; a different Layout changes
composition without changing selected facts.

For a deck, generate one v0.8 Context per view while binding the same immutable Project,
Actual, Theme and Layout resources. `examples/aster-ssd/manifest.yaml` lists that reuse;
`contexts/01-overview.yaml` shows one generated binding. Render every Context through the
same `chrona render-review` command so scheduling and presentation facts cannot drift.

[`examples/aster-ssd`](examples/aster-ssd) is the worked example: a 24-object,
28-dependency program across two work calendars, projected into four 1600x900
slides plus a tall master view. Drop `--no-raster` to also write PNG previews;
that path additionally requires node with `sharp`.

## Local authoring

### Portable icons

Create a catalog from an explicit local Iconify collection, then pass that
catalog explicitly to draft rendering. The catalog is normalized before render;
Chrona never reads raw SVG or contacts a registry at render time.
The importer writes deterministic JSON (a YAML subset) to the requested
`.yaml` path, so it remains valid YAML while large catalogs load quickly.

<!-- chrona:doc-check skip: requires an author-provided Iconify collection, notice file, and matching draft resources -->
```bash
chrona icon-catalog import icons.json --license-spdx MIT --notice-file NOTICE \
  --output icons.yaml
chrona render project.yaml --view view.yaml --theme theme.yaml --scheme scheme.yaml \
  --layout layout.yaml --icon-catalog icons.yaml \
  --visual-profile chrona-output/visual/v0.7-svg --output review.svg
```

In the View, attach a catalog entry to an existing target. `decorative: false`
requires the catalog alternative and retains the existing text as equivalent
meaning:

```yaml
visuals:
  - target: {kind: title}
    ref: chrona:risk
    side: leading
    decorative: false
```

See [Specification 64](docs/specification/64-portable-icon-catalogs.md) and
[Controller Z's icon Context](examples/controller-z/contexts/icons.yaml) for a
fully pinned materialized example.

Create a small editable project and render its first Draft with the bundled
default presentation preset:

```bash
chrona init my-chrona-project
chrona render my-chrona-project/project.yaml --actual my-chrona-project/actual.yaml \
  --viewport 1600xauto --output my-chrona-project/plan.svg
```

The resulting SVG is a Draft for review, not immutable materializer evidence.
The three generated source files are yours to edit.  Use `--preset PATH` to
choose an explicit presentation preset, or explicit View/Theme/Color Scheme/
Layout paths to override its members.

The complete reproducible HALCYON corpus remains available explicitly:

```bash
chrona init my-halcyon-example --example halcyon-1
chrona materialize my-halcyon-example/manifest.yaml \
  --slide mission-brief --output my-halcyon-example/out
```

`init` refuses a non-empty target. The HALCYON example keeps its immutable
Store closure under `.chrona/store`; commands that use a configured Store
prefer an explicit `--store-config`, otherwise discover `.chrona/store.yaml`
by walking upward from the current project directory. No home-directory or
broad filesystem fallback is used.

Materialization verifies declared generated evidence. If a reviewed source
change intentionally changes that artifact, rerun the same `chrona materialize`
command with `--write` to refresh it; without that explicit flag, a mismatch is
rejected.

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
