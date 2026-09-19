# Chrona

**Chrona** is a Git-friendly grammar for temporal project data, scheduling, and
visualization.  Its source of truth is semantic, structured data; a renderer is
a consumer, never the editor-owned authority.

This repository currently contains a Date-only reference implementation for
Core v0.1.  DateTime, time zones, DST, resource leveling, and rendering remain
deliberately out of scope.

## What is usable today

- deterministic Date / CalendarPeriod / WorkPeriod arithmetic;
- project JSON-Schema validation plus Core v0.1 semantic validation;
- endpoint-based dependency lower bounds and Date-only scheduled-span placement;
- executable conformance checks for the canonical Core v0.1 fixture.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest
chrona validate path/to/project.yaml
chrona schedule path/to/project.yaml
chrona render path/to/project.yaml --output timeline.svg
```

`chrona schedule` is a reference implementation for the acyclic Date-only
subset. It reports diagnostics for unsupported cycles rather than treating all
cycles as semantic errors.

`chrona render` is the first derived presentation slice: it projects the
resolved placements into a deterministic SVG timeline. SVG coordinates are not
project data and are never used to schedule or validate a project.

Try the included controller example:

```bash
chrona render timeline-design/docs/fixtures/controller-x.yaml --output controller-x.svg
```

The checked-in [controller timeline SVG](timeline-design/docs/fixtures/controller-x.svg)
is generated from [`controller-x.yaml`](timeline-design/docs/fixtures/controller-x.yaml).

For a broader semiconductor bring-up example with fixed and scheduled spans, working-day
exceptions, endpoint dependencies, parallel qualification work, gates, entities, and
annotations, render:

```bash
chrona render examples/controller-z-silicon-bringup.yaml --output controller-z-silicon-bringup.svg
```

## Specification

The pre-repository Core v0.1 Stable Candidate is preserved verbatim in
[`timeline-design/`](timeline-design/).  In particular, start with:

1. [`timeline-design/docs/00-vision.md`](timeline-design/docs/00-vision.md)
2. [`timeline-design/docs/03-temporal-model.md`](timeline-design/docs/03-temporal-model.md)
3. [`timeline-design/docs/04-scheduling-model.md`](timeline-design/docs/04-scheduling-model.md)
4. [`timeline-design/docs/05-project-format.md`](timeline-design/docs/05-project-format.md)
5. [`timeline-design/docs/specification/17-implementation-delivery-profile.md`](timeline-design/docs/specification/17-implementation-delivery-profile.md)

The candidate is **Proposed / Stable Candidate**, not yet Stable.  This code is
an independent conformance aid: implementation discoveries must be recorded as
diagnostics or ADR proposals, never silently rewritten into the specification.

## License

No license has been selected yet.  Do not treat this project as licensed for
reuse until a `LICENSE` file is added.
