# Design — Draft System-Font Provider (#411)

**Status:** accepted for implementation planning.

## Decision

`system` is a draft-only font asset provider.  A system declaration names an
exact family and weight; discovery resolves one installed OpenType file,
verifies its name-table family/weight, derives the existing v3 metric table
from its bytes, and gives both Layout and the raster adapter that same file.
No fallback family is accepted.

The declaration is accepted only by the draft ingress.  Immutable Context
contracts continue to permit only identity-pinned context/package locators.
`resolve_render_context`, `render-review` from an immutable closure, and
`materialize` reject any closure marked `hostFont` before rendering.

## Ownership

| Layer | Owns |
| --- | --- |
| Draft ingress | system family/weight request and volatile closure mark |
| System-font port | host discovery, exact file, actual face metadata |
| Font metrics | parsing the resolved bytes into the existing measurement model |
| Layout | measurements and completed geometry only |
| PNG adapter | passing only the resolved file to resvg, with system fallback disabled |
| Immutable closure/materializer | rejecting host-font state |

## Contract and diagnostics

Draft font configuration gains a `system` declaration with `family` and
`weight`, not a path or content identity.  A resolved result records the
requested and actual family, weight, byte identity, and a process-local path
only in `DraftRender`; it is never serialized into Scene provenance.

`E_FONT_SYSTEM_UNAVAILABLE` diagnoses an unavailable platform bridge;
`E_FONT_SYSTEM_MISSING` names the requested family/weight; and
`E_FONT_SYSTEM_MISMATCH` rejects a bridge result whose OpenType metadata does
not exactly match.  `E_FONT_SYSTEM_IMMUTABLE` rejects host-font closure state
at immutable ingress/materialization boundaries.

## Discovery portability

The product defines a `SystemFontResolver` port.  The first implementation is
the fontconfig bridge (`fc-match` with machine-readable file/family/weight
output), available on supported authoring hosts.  It must return a file and is
followed by fontTools verification, so fontconfig substitution cannot become a
silent fallback.  CoreText and DirectWrite remain platform adapter candidates:
Apple documents URL registration/discovery through CoreText, and Windows
DirectWrite exposes a system font collection and face metrics.  They are not
silently emulated by directory scans.  A host without a registered bridge
gets `E_FONT_SYSTEM_UNAVAILABLE`, not a guessed path.

## Rendering and lifecycle

SVG continues to serialize completed text without font bytes.  Draft PNG uses
the resolved file in `font_files` and keeps `skip_system_fonts=True`, ensuring
resvg paints exactly the file Layout measured.  Draft PDF and typeset targets
reject system fonts in this release: their file registration/embedding
semantics would otherwise broaden the licence and portability claim.

System-font draft output is intentionally machine-local.  It may be saved or
shared as PNG, but it cannot become immutable evidence.  There is no
interpreter/host identifier workaround and no automatic substitution.

## Acceptance

1. A draft theme selecting an installed exact face renders SVG and PNG without
   project font copying; Layout metrics and PNG use the same byte identity.
2. Missing, substituted, malformed, or unsupported-host faces diagnose
   explicitly with the requested family.
3. Immutable rendering and materialization reject host-font closure state.
4. Tests use a resolver seam plus a local real-face fixture; CI never assumes
   a commercial host font.
