# Implementation Plan: Visual Profile Fidelity Correction (#349)

**Status:** Complete
**Implements:** Specification 63 correction and #350 prerequisite

## I349-1 — Exact profile and diagnostic contract

Update Render Context schema/resources, draft closure, CLI arguments, and
`visual_capabilities` for baseline, `v0.6-svg`, and `v0.6-png` only. Migrate the
Controller Z Elevated Context to SVG profile; remove the generic v0.6 reader.
Carry capability error code, message, and pointer across the render use-case
boundary. Split Theme/Scene capability failures into value, fidelity, and limit
diagnostics with exact role-property pointers.

**Files:** Render Context schema, resource parsing, draft closure/CLI, visual
capability policy, Theme schema/resolver, fixture Contexts, focused contract and
CLI tests.

**Acceptance:** a PDF Context cannot declare a rich profile; required rich
draft preview works when explicit; baseline optional omission is deterministic;
every named diagnostic is reachable and structured.

## I349-2 — Completed gradient geometry

Replace adapter-interpreted `LinearGradient.angle` with finite Layout-plane
start/end points. Extend Scene completion to calculate endpoints from primitive
and canvas bounds using the specified clockwise-inline angle convention. Make
fidelity independent for gradient, shadow, and stroke finish. Retain only the
authorable two-stop binding contract.

**Files:** Scene model/paint/composition, SVG serializer, Theme schema, unit
fixtures for non-square geometry and invalid values.

**Acceptance:** SVG serializes `userSpaceOnUse` completed endpoints; two
differently shaped primitives retain one visible direction; no adapter computes
an angle or reads Theme/Scheme.

## I349-3 — Target/materializer release gate

Replace weak PDF byte-prefix characterization with capability-presence and
artifact-free rejection tests. Re-materialize Controller Z Elevated through the
SVG profile; characterize PNG treatment presence; assert PDF rich-profile
rejection before write. Run public materializers, output property checks,
conformance, structural checks, full parallel pytest, wheel smoke, generated
SVG audit, and GitHub CI.

**Acceptance:** target-specific profile truth is demonstrated on every route;
all release gates pass; #349 closes with its original findings answered; #350's
profile dependency is unblocked.

## Review controls

Each slice receives an architecture review and serial push. Any new effect,
stop count, target route, PDF capability, asset, icon, or renderer-local
fallback returns to Specification 63 design review first.
