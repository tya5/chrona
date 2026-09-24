# Issue 384 — Default Symbol Outline Design Correction

**Status:** accepted correction before resumed implementation  
**Date:** 2026-09-25

## Finding

The first I384-2 public-materializer diff changed every existing diamond point
mark from the rounded diamond produced by Layout's declared corner-radius to a
sharp four-line diamond.  This is a user-visible policy change and violates
Issue 384's required preservation of existing corpus appearance.

## Corrected ownership

Layout remains the owner of a completed mark's bounds and any geometry implied
by its declared `timeline.point.cornerRadius`.  Theme owns the finite symbol
selection.  Scene combines them without re-measuring or changing placement:

* when Theme selects the existing `diamond`, Scene wraps Layout's completed
  `MarkPlacement.path_commands` as `SymbolGeometry.outline`;
* when Theme selects another finite shape, Scene expands that shape against the
  same completed Layout bounds;
* the adapter receives only `SymbolGeometry.outline` in both cases and cannot
  identify or alter the selected symbol.

This does not make Layout choose an appearance.  Layout already produced its
rounded point outline under its own geometric metric; Theme still selects
whether that established diamond geometry is used.  The non-default finite
shapes deliberately have no diamond-specific rounding policy in this slice.

## Required implementation and verification update

`symbol_geometry` accepts the optional completed Layout outline and uses it
only for `diamond`.  All builder point-mark call sites pass their placement's
path commands.  Regenerate public SVGs again and require that default corpus
point paths and all non-geometry SVG content are byte-stable; expected changes
are limited to deterministic marker/pattern definition IDs and references.
