# Design Correction — Row-Density Target Capability (#400)

**Status:** accepted correction to
`issue-400-visible-row-density-policy-design-2026-09-25.md`.

## Finding

The SVG renderer already projects completed clip references.  Current Typst
and TikZ adapters do not project them.  Claiming that every adapter serializes
the compact-row clip would either make those adapters choose a different
degradation or silently lose it.

## Correction

`compact-with-warning` requires the finite `rowDensityClip` visual capability.
SVG and PNG (through completed SVG) support it in this release; PDF support is
admitted only by its existing SVG-to-PDF characterization test.  Typst and
TikZ reject a completed surface carrying that capability with
`E_VISUAL_CAPABILITY_UNSUPPORTED` until their clip projection has a separate
design and evidence.

The normal and `diagnose` paths add no capability.  Because all public
materializer profiles initially use immutable `diagnose`, the migration does
not create an unsupported public typeset artifact.  A user who explicitly
selects immutable compaction must also choose an admitted target/profile; this
is target honesty, not a fallback to un-clipped rows.
