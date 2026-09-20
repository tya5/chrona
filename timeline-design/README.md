# Timeline Design — Core Specification v0.1

This directory contains the current living, versioned design artifact set for a
Git-friendly, extensible, time-axis-centered project visualization system. Git history
preserves earlier candidates and releases.

## Status

Core Specification: **v0.1 / Stable (Date-only scheduling profile)**

The Core Specification consists of:

- `docs/specification/00-vision.md`
- `docs/specification/01-concepts.md`
- `docs/specification/02-domain-model.md`
- `docs/specification/03-temporal-model.md`
- `docs/specification/04-scheduling-model.md`
- `docs/specification/05-project-format.md`
- `docs/specification/12-quality-and-invariants.md`
- supporting ADRs, schemas, and executable-style examples

Presentation, application, successor, and implementation specifications follow the
stable Core dependency direction and remain separately versioned.

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
