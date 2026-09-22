# Issue 122 — Output Formats Design Review

## Decision

Add SVG, PNG, and PDF as named presentation targets behind a typed Renderer
registry.  A renderer consumes only a completed `SceneSurface`, viewport, and
resolved tokens, and returns an immutable `RenderArtifact` (`target_kind`,
media type, bytes, adapter identity).  It cannot receive a Project, View,
Layout, raw YAML, or font-metrics input.

`V05SvgRenderer` becomes the `svg` adapter.  `CairoSvgRenderer` is the optional
`png`/`pdf` adapter: it first uses the same SVG serializer, then asks CairoSVG
to convert those bytes.  That sequence is serialization only; it introduces no
second Layout, Scene, text measurement, or route calculation path.

## Context and reproducibility

Introduce Render Context v0.7 and migrate every materializable v0.6 Context in
one atomic slice.  v0.6 support is removed rather than retained as a compatibility
branch.  Its `target` declares exactly one `kind` (`svg`, `png`, or `pdf`) and
a sorted list of required capabilities.  PNG/PDF contexts additionally declare:

```yaml
environment:
  rasterizer:
    engine: cairosvg
    version: 2.9.1
    cairoVersion: 1.18.4
    dpi: 96
```

The adapter verifies all four values against its installed backend before
serialization.  Absence, an unavailable optional dependency, or a version/Cairo
mismatch rejects with `E_RENDER_RASTERIZER_UNAVAILABLE` or
`E_RENDER_RASTERIZER_IDENTITY`; it never substitutes a host backend.  SVG has no
rasterizer declaration.  This binds the native Cairo implementation as well as
the Python package, which is necessary for an immutable claim.

`chrona render` creates the equivalent v0.7 in-memory draft Context from its
explicit `--format` value.  `chrona render-review --format` is optional only as
an assertion: it must equal the Context target or rejects with
`E_RENDER_FORMAT_CONTEXT`.  Thus immutable evidence never changes format by a
CLI override.  Both commands resolve the same registry and use case.

## Capability and artifact policy

| Target | Preserves | Required treatment |
|---|---|---|
| SVG | source metadata, accessible/selectable text, semantic roles, markers, table semantics, hierarchical axis | Current baseline; required capabilities must all be available. |
| PNG | visual geometry and paint only | Reject any required semantic/accessibility/metadata capability with `E_OUTPUT_CAPABILITY_MISSING`; no silent loss. |
| PDF | visual geometry and text where CairoSVG emits it; no reliable source metadata, semantic roles, or table structure | Use only a declared capability profile; reject unavailable requirements. |

The use case validates the target requirements against its selected renderer
before writing an artifact.  CLI output is binary (`write_bytes`) for every
target.  The public materializer remains immutable SVG evidence in this issue;
new PNG/PDF target fixtures prove backend identity and exact bytes under the
pinned test environment, without replacing SVG fixtures.

## Whole-architecture consistency review

Core owns only `RenderArtifact` and the narrow Renderer protocol.  Presentation
owns target profiles, registry selection, concrete adapters, and Context target
validation.  The closure owns typed resource/environment binding; the review use
case remains the sole scheduler → projection → content → measurement → Layout →
Scene orchestrator.  CLI owns option parsing and writing opaque artifact bytes.
No format branch enters Project, scheduling, View, Layout, Scene, Theme, or
materializer semantics.

This conforms to ADR-0018: unsupported fidelity is rejected rather than hidden.
It does not add PPTX, embedded images, a renderer-specific authoring dialect,
or compatibility handling for the superseded Context version.

## Acceptance

- Fake renderers prove typed artifact propagation without concrete adapter calls.
- v0.7 schemas reject invalid target/rasterizer declarations deterministically.
- SVG bytes remain unchanged after the Context migration.
- PNG/PDF tests prove media signatures, pinned-backend byte repeatability, and
  missing/mismatched-backend diagnostics.
- Draft and immutable CLI paths select one registry; immutable format mismatch
  never writes an artifact.
