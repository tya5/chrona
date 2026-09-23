# Issue #258 Honest Draft Typeset Targets Design

**Status:** Accepted  
**Date:** 2026-09-23  
**Depends on:** Render Context v0.8 typesetter contract, #149 typeset-context completion

## Decision

Draft rendering continues to advertise `svg`, `png`, `pdf`, `typst`, and `tikz`.
For `typst` and `tikz`, both `chrona render` and `chrona render-workspace`
require one complete explicit typesetter descriptor:

```text
--typesetter-engine ENGINE
--typesetter-version VERSION
--typesetter-adapter-grammar GRAMMAR
```

The descriptor is passed as typed `TypesetterIdentity` input to the common
Draft closure factory.  Draft ingress never probes an installed executable,
uses a sentinel version, or silently chooses an engine.  The established target
invariants apply unchanged: Typst requires `typst` and `chrona-typst/v0.1`;
TikZ requires `tectonic` and `chrona-tikz/v0.1`.  `VERSION` is a non-empty
author-declared exact identity.

For `svg`, `png`, and `pdf`, all descriptor switches are rejected as a command
syntax error.  For a typeset target, an absent descriptor or a partial
descriptor is rejected before closure construction with
`E_RENDER_TYPESETTER_DESCRIPTOR`; an incompatible complete descriptor is
rejected by the existing typed Render Context validation as
`E_RENDER_CONTEXT_SCHEMA`.  Parser help states these conditional requirements.

The Draft artifact remains non-reproducible evidence: an explicit descriptor
records intent for deterministic source generation, but does not assert that a
host executable is installed or that a compiled host result is immutable
evidence.  `render-review` remains Context-only, accepts no Draft descriptor,
and retains its pinned target/environment identity unchanged.

## Boundary and data flow

```text
CLI descriptor switches
  -> TypesetterIdentity
  -> explicit or guided Draft closure
  -> Render Context v0.8 validation
  -> completed Scene -> typeset adapter -> UTF-8 source
```

CLI owns argument completeness and help.  The closure factory owns converting
the typed descriptor into the Draft Context environment.  The Context schema
owns target/engine/grammar validity.  Layout still owns geometry; Scene still
owns completed primitives; adapters only serialize them.  No typesetter is
consulted by Layout, Scene, or an adapter.

## Non-goals

This does not add native text reflow, automatic executable discovery, typeset
compilation, a descriptor YAML resource, a new Context version, or a fallback
target.  It does not change immutable Context rendering, raster target policy,
or public SVG materialization.
