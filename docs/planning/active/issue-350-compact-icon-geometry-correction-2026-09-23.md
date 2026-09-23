# Design Correction: Compact Normalized Icon Geometry (#350)

**Status:** Complete — supersedes the v0.2 bundled-catalog representation
decision before I350R-3 publication.

## Evidence

The complete 2,336-entry Material Symbols Outline Rounded default generated as
v0.2 object-per-command YAML is 17,924,767 bytes and did not complete a typed
contract load within two minutes on the development baseline.  This is a
structural failure, not an acceptable packaging trade-off: Context closure must
remain practical before any Layout request can use the default.

## Corrected successor contract

`icon-catalog/v0.3` replaces v0.2.  A normalized vector path retains its
paint/stroke fields but encodes geometry as one canonical, whitespace-separated
`M`, `L`, `Q`, `Z` token stream.  It is not source SVG: the importer has already
removed XML, transforms, relative commands, cubics, arcs, styling, and unsafe
features; only the fixed renderer-neutral primitive grammar survives.  The
contract parser validates finite coordinates and command arity, then produces
typed command objects.  Layout, Scene, and adapters never parse text geometry.

This eliminates repeated YAML mapping keys and millions of frozen mapping
objects while preserving exact closure identity and primitive geometry.  The
compact grammar is versioned rather than added as an optional v0.2 alternate,
so there is no valid-but-unprojected or compatibility parsing door.  The
predecessor v0.2 schema/reader/fixtures are removed together with its Context
successor reference (`render-context/v0.12`).

## Revised acceptance gates

The complete fixed selection and manifest remain required.  The generated
catalog must parse through its typed contract in at most 10 seconds on the
release baseline using PyYAML's safe LibYAML loader, be no more than 4,000,000
uncompressed bytes and 1,000,000 gzip-9 bytes, and retain the prior provenance, Apache-2.0 notice, aliases, and
offline closure checks.  Failure of any gate blocks publication; reducing the
selection, restoring raw SVG, or making a renderer parse geometry is not an
allowed workaround.

## Whole-architecture review

The correction strengthens existing boundaries.  Ingress alone owns source SVG
parsing and lowering; contract parsing is resource validation, not layout or
adapter interpretation.  Context still closes exact ordinary catalog bytes;
Theme still owns paint; Layout still owns placement; Scene still receives
completed typed paths.  A versioned resource replacement is clean because the
project explicitly does not retain compatibility when it harms design.
