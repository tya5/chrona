# Implementation Plan: Visual Capability Feedback Correction (#349)

**Status:** Complete — I349F-1 through I349F-3 accepted
**Implements:** Specification 63 diagnostic amendment and architecture review

## I349F-1 — Structured capability diagnostic transport

Add canonical messages for the closed visual-capability diagnostic vocabulary.
Adapt `SceneBuildError` at `render_review` into `RenderFailed` using its stable
code, stored role-property pointer, and canonical message. Keep existing
fallback behaviour for non-capability Scene errors.

**Files:** `presentation/scene/visual_capabilities.py`,
`presentation/scene/v05_builder.py`, `usecases/render_review.py`, focused Scene
and use-case tests.

**Acceptance:** a baseline render of the elevated Theme fails before renderer
invocation with `E_VISUAL_CAPABILITY_UNSUPPORTED`,
`/body/roles/group-band/gradientAngle`, and an explanatory message in both the
use case and CLI envelope.

## I349F-2 — Completed icon capability provenance

Carry the View `iconBindings` array-item pointer through the Layout placement
and completed Icon primitive. Use it only in pre-adapter profile validation so
an unsupported vector/raster icon identifies the author binding. Do not alter
adapter input, icon asset closure, or profile capabilities.

**Files:** Layout placement model/composer, Scene model/projection, visual
profile validator, focused model/validator tests.

**Acceptance:** an Icon completed for a baseline profile is rejected before
adapter invocation with an exact `/body/iconBindings/<index>` pointer and an
icon-specific message.

## I349F-3 — Policy and target evidence

Add fixtures proving `decorative-optional` effects are omitted at Scene
completion for baseline while required effects reject. Extend materializer
evidence with SVG structural assertions and a PNG pixel comparison that proves
the admitted rich treatment affects output. Retain PDF only as artifact-free
rich-profile rejection; remove no route and add no PDF approximation.

**Files:** visual capability, Scene, CLI, materializer/output tests and
Controller Z fixture only if a deterministic optional fixture is required.

**Acceptance:** focused tests, full pytest, conformance, public materializer
checks, wheel smoke, generated artifact audit, and CI pass. The final review
records that #349 feedback is closed without expanding visual capability scope.

## Publication units

1. Publish this implementation plan.
2. Publish I349F-1 and I349F-2 together because a public diagnostic must be
   structurally complete across both Theme and icon paths.
3. Publish I349F-3 evidence and the release review after the full gate.
