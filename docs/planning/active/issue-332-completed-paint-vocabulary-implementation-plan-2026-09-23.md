# Implementation Plan: Completed Scene Paint (#332)

**Design inputs:** Specification 46 and the #332 architecture review of
2026-09-23.  This plan intentionally changes the incomplete role-only Scene
contract without a compatibility path.

## P332-1 — Typed contract and Theme validation

**Files:** `scene/model.py`, `model/theme_tokens.py`,
`schemas/theme-v0.4.schema.yaml`, Theme/Scene unit tests.

**Change:** Add immutable `ScenePaint` and surface canvas paint. Extend Theme
role bindings with validated `strokeWidth` and `dashPattern` token access.
Introduce a dedicated resolver that validates the channel contract before Scene
construction. Add a closed semantic primitive-family mapping rather than
spreading role-name checks through builders.

**Acceptance:** Invalid/missing fill, stroke, width, invalid declared opacity, and dash report
stable diagnostics; fill-only, stroke-only, and mixed paint resolve exactly;
no global value is used as a default.

## P332-2 — Complete Scene projection

**Files:** `scene/v05_builder.py`, Scene builder tests and fixtures, public
Scene inspection tests.

**Change:** Resolve canvas and every table-timeline/dependency-network
primitive through the P332-1 resolver. Move opacity into `ScenePaint`; retain
`visual_role` only for traceability. Cover dynamic legend/category roles,
patterns, paths, text, symbols, and all optional content families.

**Acceptance:** A completed `SceneSurface` has no adapter-required token lookup;
every primitive satisfies its family channel contract; unchanged semantic inputs
retain identities and geometry.

## P332-3 — Renderer isolation and exact serialization

**Files:** SVG and typeset renderers, renderer tests, render entry-point tests.

**Change:** Remove `ThemeTokenView` from renderer inputs and imports. Serialize
completed paint in SVG and TikZ, including mixed channels, width and dash.
Validate target support before artifact creation; remove hard-coded hatch paint
width. Keep target-specific syntax only at this boundary.

**Acceptance:** Renderer source has no Theme/Scheme import; byte assertions
prove exact SVG/TikZ output for each channel; unsupported form rejects rather
than downgrading.

## P332-4 — Public evidence and release gate

**Files:** materializer checks/fixtures, generated SVG evidence, current review
document.

**Change:** Regenerate affected public materializer evidence only after P332-3,
then compare intentional SVG changes and add structural gates for completed
paint/adaptor isolation.

**Acceptance:** focused tests, full `pytest`, public materializer checks, and
generated SVG comparison pass. The final review maps each #332 criterion to
evidence; #315 is closed only after that review is public.

## Sequencing and publication

Each slice is committed, verified, and pushed serially. Before each push,
re-check remote `main`, local diff, and target commit. If a slice exposes a
missing semantic channel or a cross-boundary responsibility conflict, stop
implementation, amend Specification 46 and its review, publish the correction,
then resume from the corrected design.
