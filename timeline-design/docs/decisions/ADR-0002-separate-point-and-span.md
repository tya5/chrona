# ADR-0002: Keep TemporalPoint and TemporalSpan Separate

**Status:** Accepted for Core v0.1

## Context

A point could be encoded as a span whose start equals end, but this creates an empty
half-open interval and conflates different editing and semantic behavior.

## Decision

TemporalPoint and TemporalSpan are separate core primitives.

## Consequences

Point has endpoint `at`. Span has endpoints `start` and `end`. Profiles such as
milestone inherit from Point; task and phase inherit from Span.
