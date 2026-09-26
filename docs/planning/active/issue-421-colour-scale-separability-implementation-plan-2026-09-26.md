# Implementation Plan — Colour Scale Separability (#421)

## I421-1: checker, transport, scheme fixes

**Files:**
- new `presentation/model/color_separability.py`;
- `model/color_scale.py` (collisions);
- `usecases/render_review.py` (claims in; warnings and Scene diagnostics out);
- `app/cli.py` (emit);
- `examples/halcyon-1/schemes/{control-room-dark,mission-light}.yaml`;
- Specification 60 (the minimum and the method);
- tests: unit for separability and scale, CLI, and the corpus gate.

**Evidence:** the batch of 21. Changes are limited to the `launch`/`ops` category colours on slides using these two schemes.

**Gate:** focused tests, conformance, CI.

## I421-2: acceptance review, then close #421
