# ADR-0004: Separate Domain Semantics from Project Format

**Status:** Accepted for Core v0.1

## Context

A text format is required for Git-native persistence, but serialization conveniences
should not define domain meaning.

## Decision

Domain, Temporal, and Scheduling specifications define semantics. Project Format
defines YAML representation and normalization.

## Consequences

The format may evolve or add shorthand without redefining semantics. Alternative
serializations remain possible.
