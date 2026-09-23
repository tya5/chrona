# Design Plan: Visual Capability Feedback Correction (#349)

**Status:** Active
**Issue:** #349 post-hoc review feedback
**Corrects:** Specification 63 and the #349 release evidence

## Objective

Close the remaining author-facing diagnostic and target-evidence gaps without
changing the closed v0.6/v0.7 capability vocabulary or admitting a new target.
A required unsupported treatment must preserve a useful, exact diagnostic
through every boundary; an optional treatment must be proven omitted only by
Scene policy; and SVG/PNG evidence must demonstrate the policy at the public
render route.

## Verified starting facts

- `ScenePaintError` and `SceneBuildError` preserve a role-property pointer,
  but `render_review` converts the latter using `str(error)`. This makes the
  public failure message the diagnostic code and drops the pointer.
- `validate_surface_visual_profile` independently rejects completed required
  treatments but constructs `VisualCapabilityError` without a property path or
  explanatory message.
- The current tests prove required rejection at the unit boundary, but do not
  prove the public baseline diagnostic, optional omission, or pixel/serialized
  PNG treatment evidence.
- The profile matrix remains exact: baseline is available on all targets;
  v0.6/v0.7 rich profiles are available only for SVG/PNG. No PDF, Typst, or
  TikZ rich admission is in scope.

## Design questions

1. Define one typed capability diagnostic payload that can carry stable code,
   source pointer, and human-readable message from Theme completion and
   completed-surface validation to `RenderFailed` and CLI output.
2. Define completed-treatment provenance sufficient for surface validation to
   retain a role-property pointer, without allowing adapters to read Theme or
   select policy.
3. Define target evidence that distinguishes deterministic optional omission,
   required pre-serialization rejection, and presence of an admitted SVG/PNG
   treatment.

## Whole-architecture constraints

- Theme owns role bindings; Scene owns completion and optional omission;
  `VisualProfile` owns target admission; adapters only serialize completed
  primitives.
- Layout remains the sole owner of bounds and placement. Neither diagnostics
  nor target evidence may move geometry or treatment selection into Layout or
  adapters.
- Context-selected exact profiles remain immutable inputs. Do not introduce a
  generic profile, fallback, target inference, or compatibility alias.
- Icon v0.7 profiles are consumers of this mechanism. The correction must
  preserve their existing capability sets and independently diagnose an
  unsupported icon with its binding pointer.

## Design and publication gates

| Gate | Evidence required |
| --- | --- |
| D349F-1 | Diagnostic ownership, pointer provenance, and message contract reviewed against Theme → Scene → use case → CLI. |
| D349F-2 | Optional/required target policy and SVG/PNG evidence boundaries reviewed against Specification 63 and icon profiles. |
| D349F-3 | English design amendment and architecture review published before implementation planning. |

