# ADR-0005: Renderer State Is Not the Source of Truth

**Status:** Accepted for Core v0.1

## Context

An interactive editor such as tldraw naturally maintains shapes, coordinates, and
internal store records.

## Decision

Renderer/scene state is derived from semantic project data. tldraw Store or equivalent
renderer state MUST NOT be the semantic project source of truth.

## Consequences

Temporal x coordinates are recomputed from temporal values. UI mutations must be
translated back into semantic commands/model changes.
