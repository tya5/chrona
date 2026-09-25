# Implementation Plan — Axis and Visible Failure (#405, #406, #407, #408, #400)

**Entry condition:** design `1b4431dd` and review `5b52f0db` are published.

## I1. View/calendar contracts

Introduce View v0.16 tier declarations and calendar fiscal-start data; remove
the positional levels/ticks/timePresentation reader. Update typed contracts,
normalization, schema inventory, docs, and every corpus View atomically.
Add negative schema and contract tests for invalid tier roles, forms, `every`,
and dead combinations.

## I2. Axis Layout closure

Extend axis interval/calendar calculation for half and fiscal buckets, typed
name tables, auto/every-N selection, per-tier placement/alignment, and recorded
outcomes. Assert every tier is consumed. Scene receives completed labels/grid/
band placements only.

## I3. Failure registry and row-policy integration

Implement the finite classification registry and structured placement warnings.
Replace silent axis omission with `diagnose|thin-with-record`; replace the
unconditional row overflow path by the P1-computed requirement plus declared
draft/immutable policy. Do not duplicate P1 allocation logic.

## I4. Evidence and release

Add corpus cases for all accepted tier behaviors and failure outcomes; regenerate
public materializer artifacts. Run focused tests, full pytest, all materializers,
coverage/structural checks, wheel smoke, visual acceptance review, and
three-platform CI before closing the programme.
