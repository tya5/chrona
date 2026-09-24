# Implementation Plan: Slot-owned icon placement correction (#375)

**Status:** Accepted.

**Implements:** [slot-owned icon placement correction](../../design/issue-375-slot-owned-icon-placement-correction-2026-09-25.md)

## C375-1 — Complete icon owners in Layout

Add one local Layout owner resolver over declared slots.  Normalize text owners
before ordinary text-visual resolution; give candidate plot/variance visuals
their resolved host slot at construction; give annotation and note-index
visuals the known annotation slot at construction.  Remove the `annotations`
fallback entirely.

**Files:** `surface_composer.py` and focused placement tests only.

**Acceptance:** no icon reaches `SurfacePlacement` without a declared slot;
the resolver has no Scene import or primitive-ID/purpose/geometry inference.

## C375-2 — Characterize optional-slot and host classes

Retain the three previously failing draft cases and add direct assertions that
plot label, variance label, table/group-header, annotation, and mark visual
icons use their host's completed Layout slot.  Include a negative missing-owner
case where practical.

**Acceptance:** each class proves the intended owner and a surface without
`annotations` remains materializable.

## C375-3 — Release gate

Run focused tests, all public materializer byte checks, generated-report checks,
conformance, full pytest, reachability/import-direction, installed-wheel smoke,
and three-platform CI.  Amend the #375 acceptance review with the correction
and close #375 only after the final CI succeeds.
