# Implementation Plan: Portable Visual Capabilities (#345)

**Status:** Active  
**Implements:** Specification 63 and UC-32

## I345-1 — Profile and resource contract closure

Add a versioned visual profile field to Render Context and closed Theme v0.5
bindings for gradient, shadow, cap, and join. Validate all finite ranges,
role/Scheme color bindings, capability IDs, fidelity, and target/profile
compatibility before Scene construction. Migrate all current contexts atomically
to the baseline profile; no v0.4 Theme or unprofiled Context reader remains.

**Acceptance:** invalid values/literals/unsupported required capabilities have
stable diagnostics before artifact write; ordinary existing output is unchanged.

## I345-2 — Completed compositional Scene values

Extend `ScenePaint` with immutable completed linear gradient, drop shadow, and
stroke finish values. Extend the sole
Theme/Scheme resolver and Scene projection; Layout remains geometry-only.

**Acceptance:** source identity and geometry are unchanged by treatment;
completed Scene contains no token IDs, target syntax, fallback choice, or
unbounded value; focused resolver/projection tests pass.

## I345-3 — Target adapters and fidelity gate

Implement SVG v0.6 definitions/attributes and deterministic IDs. PNG/PDF use
the pinned SVG route only after profile validation. Typst/TikZ reject required
v0.6 capability. Add a structural test forbidding Theme/Scheme imports and
capability-policy selection in adapters.

**Acceptance:** SVG byte fixtures serialize the completed value; unsupported
required output is artifact-free; optional omission is decided before adapter.

## I345-4 — Public paired gallery evidence and release

Add a portable enhanced gallery direction only after I345-1--3. It shares the
Controller Z semantic fixture, declares accessibility evidence, and is produced
through the public materializer. Run focused tests, full parallel pytest,
conformance, structural checks, materializer bytes, batched SVG diff, wheel
smoke, and GitHub CI.

## Review controls

Each slice receives an implementation architecture review and serial push.
Any image, path clip, radial gradient, new effect, geometry type, target adapter,
or package integration returns to Specification 63 design review first.
