# Design Plan — Explicit Unfilled SVG Paint (#456)

## Published baseline and scope

At `92403bb1`, completed Scene paint permits a stroke without a fill
(`docs/specification/46-completed-scene-paint.md`). `v05_svg.py` serializes
stroke-only Rect and Symbol primitives without a `fill` attribute. SVG then
applies its initial black fill. Issue #456 identifies 844 closed-day rectangles
on 19 committed slides and 12 print-theme milestone Symbols, including the
README hero. The Scene contrast report for #431 observes declared channels,
so it cannot by itself prove the current SVG pixels.

The original #431 contrast measurements of closed days were corrected in the
issue comments. The published Scene contrast policy and its generated report
remain useful once adapter output agrees with the completed paint.

## Literal acceptance to prove

1. Every committed SVG shape outside `<clipPath>` has an explicit `fill`.
2. Closed days on every committed slide paint as declared, with no black
   stripes.
3. Print-theme outline milestones remain hollow.

The PNG route serializes through SVG, so a representative PNG must be checked
too. #431's five-decoration visibility criterion must be re-reviewed from the
corrected output, not inferred from the Scene report alone.

## Design decisions to complete

1. Define the renderer-neutral meaning of absent `ScenePaint.fill` at the SVG
   boundary, including Rect, Symbol, paths, marker definitions, and clip
   geometry. Ensure SVG defaults cannot override completed paint.
2. Review the current `calendar-closed` treatment, stroke, width, and opacity
   in every public Theme. Choose whether each appearance is an outline or a
   filled tint; preserve a clearly declared choice and the #431 contrast floor.
3. Define an artifact-level check over committed SVGs that excludes clipPath
   geometry but detects any future drawable shape with implicit fill.
4. Identify the exact public materializers and generated SVG/PNG evidence that
   must change together. Inspect the README hero and the print-theme outline
   milestone after regeneration.

## Dependency and publication order

Publish this plan; publish the completed design, normative specification
correction, and architecture review; publish an implementation plan; then
implement and regenerate in one reviewable slice. Run focused adapter and
artifact checks, affected public materializer reproduction, and one CI release
gate. Publish an acceptance review mapping all three literal criteria before
closing #456 or reconsidering #431.

If the visual inspection disproves the selected Theme treatment, return to
design and republish a correction before changing Theme values.
