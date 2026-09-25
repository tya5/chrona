# Design Correction — Draft System-Font Ingress (#411)

**Status:** accepted correction to
`issue-411-draft-system-font-provider-2026-09-25.md`.

## Corrected decision

The draft-only system-font selection is the explicit `chrona render
--system-fonts` opt-in.  It is not a third `fontMetrics` descriptor and it
does not introduce a new authored font configuration file.

The resolved Theme remains the single request authority: its `text` role
selects the requested family and its declared text weights select each exact
face needed by Layout.  With the opt-in absent, draft rendering retains the
existing declared-metrics-v3 closure.  With it present, draft ingress asks the
system-font resolver for each needed Theme family/weight face before Layout.

## Why this corrects the prior wording

The prior document said that “draft font configuration gains a `system`
declaration”.  That conflicts with the integrated typography design, which
already specifies `--system-fonts`, and would create two authorities for the
same face: an authored config family/weight and a Theme family/weight.  It
would also invite an accidental serialisation path through `fontMetrics`.

The flag is a volatile authoring capability, not a project resource.  Its
result is a `DraftFontResolution` held only by `DraftRender` and forwarded
explicitly to a draft `RenderRequest` and the PNG renderer.  It contains the
requested/actual family and weight, source and generated-metrics identities,
the exact metrics model, and a process-local path.  Neither the path nor the
resolution enters `RenderContextContract`, Store data, Scene provenance, or
materializer inputs.

## Boundary and target policy

`--system-fonts` is accepted only by draft `chrona render`; guided workspace
rendering does not silently acquire host capability in this release.  The
normal immutable `render-review` and `materialize` APIs have no argument that
can carry a `DraftFontResolution`.  Their declared context/package font
closure remains the sole accepted font source.  Defensive request validation
must reject a resolution passed to either immutable pathway with
`E_FONT_SYSTEM_IMMUTABLE`.

SVG receives only completed geometry and the requested family names.  Draft
PNG receives only the exact resolved files and continues to set
`skip_system_fonts=True`; the flag never enables arbitrary renderer host
discovery.  PDF, Typst, and TikZ draft output reject a system resolution with
`E_FONT_SYSTEM_IMMUTABLE` until their embedding and licence semantics have a
separate design.

## Implementation-plan amendment

I411-2 must implement the CLI flag, Theme-derived face selection, and typed
volatile handoff.  It must not add a system provider to Context schemas or
reuse `--font-metrics` as a system configuration channel.  I411-3 acceptance
must prove the CLI ingress, no-host-path Context/Scene serialization, and
rejection on non-PNG draft targets as well as immutable pathways.
