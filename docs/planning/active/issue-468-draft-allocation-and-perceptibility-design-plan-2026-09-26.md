# Design Plan — Coherent Draft Allocation and Starter Perceptibility (#468)

## Published baseline and measured failure

At `2ae1111682d1a101780864657ccabc6ffbcb8ff7`, #468 is open with no
comments. A current bare `chrona render examples/halcyon-1/project.yaml`
(with required `--output`) succeeds but reports 15 `W_LAYOUT_MARK_OVERFLOW`,
8 `W_LAYOUT_ROW_DENSITY` and 4 `W_SCENE_TEXT_INTERSECTION`. The `table` and
`review-surface` slots end at y=785.2, `timeline` ends at y=785.2, and `notes`
begins at y=805.2, while emitted rows continue into that notes band. The
draft View has no axis tiers. These are observed public-output facts, not an
assumption that an older handoff's measurements still hold.

Current code computes a content-derived `required_block` for every table-
timeline request but applies it to final slot allocation only when
`request.draft_auto_block` is true. Otherwise `surface_composer` expands the
completed canvas around escaped primitives without re-solving the profile.
CLI and Draft API defaults remain `(1600, 900)`. The #446 Scene evaluator
already detects text intersections, but its CI gate scans committed generated
Scenes, not the default starter render.

## Literal issue acceptance

1. `chrona render examples/halcyon-1/project.yaml` with no flags emits no `W_LAYOUT_MARK_OVERFLOW`, `W_LAYOUT_ROW_DENSITY` or `W_SCENE_TEXT_INTERSECTION`.
2. With an explicit `--viewport 1600x900` on the same project, overflowing rows stay inside the `timeline` and `table` slots or grow them together; no note is overprinted. A test covers this.
3. The default draft render shows month labels on the timeline.
4. The Scene perceptibility gate (#446) or an equivalent check fails when a text primitive intersects another one in a committed or starter render.

`--output` is syntactically required by the current CLI; the first criterion
means no other presentation/resource/viewport flags.

## Design questions and required review

1. Define whether a fixed viewport is a hard clipping rectangle or, per
   #449, a minimum requested allocation whose **whole profile** may grow.
   Specify how immutable Contexts and Draft requests share or differ in
   this rule, including all slot/notes movement and completion evidence.
2. Define a single Layout-owned content extent and reallocation function,
   avoiding a caller-side second geometry policy. Check the shape against
   #365 Draft auto, #449 visible fallback, Specification 33 layout,
   Specification 08 Scene, Specification 50 surface quality, and ADR-0031.
3. Select the exact default Draft viewport for CLI, guided/workspace and
   typed Draft ingress; remove inconsistent duplicate defaults. Define the
   month/quarter tiers and font-fit/overflow behavior of the bundled default
   View without changing existing public Views implicitly.
4. Decide how the existing pure #446 evaluator checks the starter render in
   CI without duplicating its algorithm, admitting a warning-only result, or
   conflating a research mock with product evidence. Examine real rendered
   SVG and Scene, not a Scene-only proxy for user-visible acceptance.
5. Record schema/resource version and Context pin effects (if any), changed
   generated Scene/SVG bytes, migration intent and negative tests. Check
   extension to larger projects and non-table surfaces without a special-
   case keyed to HALCYON-1.

## Design and publication slices

Publish design and whole-architecture review before product code. Then
publish an implementation plan with independent units for (a) coherent
allocation, (b) default Draft View/ingress, and (c) starter perceptibility
gate and release evidence, each with focused tests. Any semantic or normative
change updates a living specification/ADR in the design phase. During
implementation, a discovered policy gap returns to design/review/plan and is
published before code resumes. Each accepted unit gets focused tests and a
serial publication; final acceptance requires public materializer byte/diff
audit, full CI matrix, actual SVG observation and all four literal rows.
