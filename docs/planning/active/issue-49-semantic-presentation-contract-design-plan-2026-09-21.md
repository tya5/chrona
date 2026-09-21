# Issue #49 semantic presentation-contract refactor design plan

## Purpose

Close the structural gap exposed by the #47 external verification: presentation meaning is currently repeated across authoring inputs, Scene composition, theme keys, tests, and example evidence. The recovery work must consolidate that meaning before further feature-level repairs.

## Scope

This design phase defines:

1. a normalized presentation contract produced at the authoring boundary;
2. a single semantic registry for primitive roles, required/optional theme capabilities, and evidence expectations;
3. a measured placement model that separates layout from Scene emission;
4. a compatibility adapter at ingress only; and
5. contract-driven unit, integration, and materialization verification.

It does not restore the deleted legacy Settings/Theme contract and does not add renderer-specific or hand-authored generated SVG paths.

## Design sequence

1. Inventory each current duplicated presentation meaning and its owners.
2. Specify the normalized contract and its invariants.
3. Specify the semantic registry, including canonical names and aliases accepted only at ingress.
4. Specify Layout-to-Scene handoff and reject implicit geometry decisions in Scene composition.
5. Specify verification closure from contract to theme to materializer evidence.
6. Review the result against the existing Project, Actual, View, Layout, Scene, Theme, and Materializer boundaries.
7. Publish an implementation plan only after all six design decisions are closed.

## Completion criteria

- Every presentation feature has one canonical semantic name and one authoritative producer.
- Legacy spelling is normalized before contract construction and cannot leak downstream.
- Scene composition consumes normalized semantics and measured placements, not raw authoring switches or theme-key fallbacks.
- A contract test can enumerate required theme bindings and expected Scene primitives.
- The refactor preserves the stated #49 acceptance outcomes and retains only explicit public-input compatibility.
