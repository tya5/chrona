# Timeline Design — Core Specification v0.1

This repository snapshot contains the initial design artifact set for a Git-friendly,
extensible, time-axis-centered project visualization system.

## Status

Core Specification: **v0.1 / Draft**

The Core Specification consists of:

- `docs/00-vision.md`
- `docs/01-concepts.md`
- `docs/02-domain-model.md`
- `docs/03-temporal-model.md`
- `docs/04-scheduling-model.md`
- `docs/05-project-format.md`
- `docs/12-quality-and-invariants.md`
- supporting ADRs, schemas, and executable-style examples

Presentation and implementation specifications are intentionally deferred until the
Core semantics are stable enough to constrain them.

## Reading order

1. Design Documentation Plan
2. Vision
3. Concepts
4. Domain Model
5. Temporal Model
6. Scheduling Model
7. Project Format
8. Quality and Invariants
9. ADRs and examples as supporting material

## Core boundary

The project is defined by semantic project data and deterministic temporal/scheduling
rules. A renderer such as tldraw is a consumer of the model, not its source of truth.
