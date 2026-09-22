# Typeset Render Context Completion Design Correction

## Decision

D6 is completed as follows.  Render Context v0.8 replaces v0.7 atomically.
Its `target` carries `kind`, `capabilities`, and the required
`textMode: positioned` for `typst` and `tikz`.  Its `environment.typesetter`
is required for those two targets and is absent for `svg`, `png`, and `pdf`.
It contains exactly `engine`, `version`, and `adapterGrammar`.

The supported immutable descriptors are:

| target kind | engine | adapter grammar | artifact media type |
| --- | --- | --- | --- |
| `typst` | `typst` | `chrona-typst/v0.1` | `application/x-typst` |
| `tikz` | `tectonic` | `chrona-tikz/v0.1` | `application/x-tex` |

`version` is a non-empty exact engine version recorded by the author.  A
valid Context never uses a sentinel such as `unavailable`, `latest`, or a
range.  Source serialization does not execute, discover, or validate the
host engine: the descriptor identifies the toolchain that may be used by an
optional verification job.  That job compiles only when the installed engine
and its exact version equal the Context descriptor; its host-produced output
is explicitly non-immutable evidence.

Draft ingress may create a typeset Context only after resolving the selected
engine's installed exact version.  If it is unavailable, draft render rejects
with `E_RENDER_TYPESETTER_UNAVAILABLE`; it must not synthesize an ambiguous
Context.  Immutable Context closure resolution remains host-independent.

## Positioned source contract

The completed Scene coordinate system is serialized as points: one Chrona
Scene unit is one target `pt`.  The viewport creates a zero-margin page/canvas
of the same point dimensions.  Both adapters invert neither geometry nor
recompute a baseline: a Text primitive is emitted at its supplied baseline
with its supplied bounds, family, weight, size, and line policy.  The source
contains its `font_asset_identity` as deterministic source metadata and uses
the supplied family as its explicit target font declaration.  The descriptor
does not claim the host has that font; host typeset output remains non-evidence.

Primitive emission follows completed `SceneSurface.primitives` order exactly;
escaping and numeric formatting are adapter grammar behavior fixed by
`adapterGrammar`.  The adapters may map Rect, Text, Symbol, and Path to native
vector commands only.  They receive only `SceneSurface`, viewport, and
resolved tokens and have no layout, resource, scheduling, routing, or font
metric dependency.

## Capability and artifact boundary

`typst` and `tikz` start with an empty preservable-capability set.  Existing
capability validation therefore rejects SVG semantic/accessibility/table
requirements rather than creating target-specific approximations.  The
artifact is deterministic UTF-8 source with target kind, media type, and
adapter grammar identity.  Artifact writing is the existing CLI/use-case
output responsibility; compilation is not part of rendering.

## Whole-architecture review

This correction keeps Specification 08's `Layout -> Scene -> renderer` seam:
units, text measurements, and placements are completed before an adapter runs.
It keeps Specification 09's CLI boundary because toolchain lookup belongs only
to draft Context construction, not rendering or CLI output handling.  It keeps
Specification 13's immutable closure rule because a persisted descriptor is
read, not replaced from the host.  It also strengthens D6's evidence rule by
making a missing toolchain a draft-ingress rejection instead of silently
weakening an immutable identity.  No View, Project, presentation vocabulary,
or materializer responsibility moves as a result.
