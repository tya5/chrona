# Issue 122 — Output Formats Design Plan

## Purpose

Plan the renderer-target boundary before adding PNG or PDF output.  The result
must preserve the completed `SceneSurface` handoff: rasterization may serialize
an SVG-equivalent surface, but may not measure text, select layout, alter routes,
or become a second render pipeline.

## Questions the design must close

1. Define a typed artifact/result contract for the existing `Renderer` protocol
   that identifies target kind, bytes, media type, and deterministic adapter
   identity without leaking SVG strings through a generic port.
2. Decide the Context schema evolution required to bind target format,
   capabilities, and the exact rasterizer identity/version for immutable PNG/PDF
   output.  Assess a clean Context version replacement versus an optional field;
   do not retain v0.6 compatibility merely to avoid resource migration.
3. Specify target capability profiles for SVG, PNG, and PDF, including the
   required rejection or explicit-loss diagnostics for metadata, accessibility,
   markers, and semantic table structure that a target cannot preserve.
4. Select and bound an optional raster backend.  Its absence must yield one
   stable diagnostic; its version/configuration must be declared, verified, and
   never inferred from a host installation for immutable rendering.
5. Define the CLI relationship between draft `render` and immutable
   `render-review`: both select the same target-kind registry and use the same
   use case; neither gets a format-specific Layout, Scene, or renderer branch.
6. Define byte/fixture evidence for SVG and deterministic pixel/PDF evidence
   where backend determinism can be stated, plus materializer and packaging
   requirements for optional dependencies.

## Required architecture review

The design review will trace Project/Context contracts → presentation closure →
render use case → completed Scene → renderer registry → artifact writer.  It
will verify that Core only owns a narrow port, presentation owns target and
capability policy, the CLI owns argument parsing/output I/O, and adapters own
only serialization.  It will explicitly reject renderer-local geometry,
host-default rasterizers, unpinned immutable output, and an embedded-image
PPTX shortcut.

## Deliverables and gates

1. Publish a design review with the selected contract, Context migration,
   diagnostics, capability matrix, and whole-architecture consistency result.
2. Publish a separate implementation plan with independently reviewable
   contract/schema, adapter/CLI, and verification slices.
3. Only then implement; run focused tests, complete pytest/conformance,
   structural checks, public materializers, and target-specific artifact
   verification before one implementation PR.

## Out of scope

PPTX/native slide shapes, renderer-owned presentation semantics, new Scene
primitives, font/layout changes, rasterization fallbacks, and silently lossy
formats are not part of this issue.
