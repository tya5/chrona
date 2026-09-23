# Design Plan: Completed Renderer-Neutral Paint Vocabulary (#332)

## Purpose

Issue #315-A made opacity observable while deliberately leaving stroke width,
mixed fill/stroke, and dash unfinished.  #332 completes that deferred work.
The outcome is not a larger SVG option set: a completed Scene primitive must
carry the renderer-neutral paint selected from the resolved Theme/Scheme
closure, and an adapter must only serialize that value or reject an unsupported
target capability.

## Verified starting point

`ScenePrimitive` currently carries a semantic `visual_role` and optional
opacity.  SVG and typeset adapters re-open `ThemeTokenView` for fill/stroke;
SVG hard-codes hatch width and every adapter lacks completed stroke-width/dash
data.  Theme v0.3 already has `number` and `dashPattern` token kinds, but role
bindings and the completed Scene contract do not close their use.  This is a
boundary defect, not a renderer-only feature gap.

## Design questions

1. Define a typed `ScenePaint` value with independently optional fill and
   stroke, required finite non-negative stroke width when stroke is present,
   closed dash data, and opacity.  It must be constructible only by projection
   from the resolved Theme/Scheme closure; it is not an author-provided literal
   colour escape hatch.
2. Define a closed mapping from primitive family/purpose to its required paint
   channels.  Text and solid marks need fill; connectors and rules need stroke;
   outline/hatch and any declared mixed mark need both.  Missing required
   channels diagnose before adapter invocation.
3. Decide the v0.3 Theme binding vocabulary and its schema validation for
   `strokeWidth` and `dash`, including finite values and dash-segment rules.
4. Specify SVG, Typst, and TikZ capability behavior.  A renderer serializes
   exact completed fill/stroke/width/dash values; it must not infer a fallback
   or silently discard a declared channel.
5. Specify fixtures and byte-level checks covering fill-only, stroke-only,
   mixed fill/stroke, width, solid dash, non-solid dash, opacity, and unsupported
   combinations.

## Explicit non-goals

- Field-driven colour scales (#314), progress-fill (#308), or new mark
  semantics.
- Layout geometry, routing, label fitting, or renderer-specific paint policy.
- Backward compatibility adapters for the incomplete primitive contract.

## Whole-architecture review criteria

| Boundary | Required responsibility | Prohibited responsibility |
| --- | --- | --- |
| Theme / Scheme | Declare and resolve paint policy into concrete tokens | Select Project facts or target syntax |
| Scene projection | Convert the selected role contract into typed completed paint | Invent colour, width, or dash defaults |
| Layout | Produce geometry only | Choose paint channels or rendering syntax |
| Renderer | Serialize completed paint or reject unsupported capability | Re-open Theme, calculate a width/dash, or silently downgrade |
| Schema / tests | Validate declaration and prove closure | Encode renderer defaults as resource policy |

## Required design outputs

1. A normative ScenePaint and Theme v0.3 contract in the specifications.
2. A role/purpose paint-channel table covering every current primitive family.
3. Renderer capability and diagnostics policy.
4. An implementation plan divided into independently verifiable, publishable
   slices: contract/schema, projection closure, adapter serialization, and
   acceptance evidence.
5. A design review that checks the new contract against View, Layout, Scene,
   Theme/Scheme, materializer, and all public adapter boundaries.

## Publication gate

Publish this plan first.  Publish the completed design and its architecture
review next.  Only then begin implementation.  Each implementation slice gets
focused tests; the final slice additionally runs the full suite, public
materializer checks, and generated SVG comparison before #332 and then #315
can close.
