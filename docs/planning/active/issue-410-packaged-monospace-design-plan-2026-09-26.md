# Design Plan — Packaged Monospace Measurement Closure (#410)

## Purpose

Complete the unfulfilled monospace acceptance criterion of #410 without
turning Theme `fontFamily` into adapter-local font fallback.  The existing
typed treatment and numeric-spacing work is retained; this plan addresses the
remaining fact that Layout currently receives one global `FontMetrics` value
even though a Theme role may name another family.

## Established facts

- Theme v0.11 has a finite `TextTreatment.family` and `weight`, and completed
  text placements already retain the selected font asset identity.
- The declared font descriptor can enumerate assets by family and weight, but
  the current Layout request resolves only one metrics object before a role is
  measured.
- The primary wheel contains Noto Sans regular/bold and has a 5 MB size gate;
  it contains no monospace face.
- The #410 issue requires one usable bundled monospace family.  I410-2
  deliberately excluded it, so that slice cannot close the issue by itself.

## Design questions

1. Define a typed immutable font-metrics catalog keyed by the exact selected
   `(family, weight)` rather than allowing a caller or adapter to choose a
   nearby face.
2. Define the failure boundary for an unknown role face/weight, including the
   distinction between an invalid declared resource and a missing glyph
   substitute.
3. Specify a single licensed Noto Sans Mono face, its imported v3 metrics,
   Context descriptor entries, package inclusion, identity provenance, and
   wheel-budget evidence.
4. Trace role-local metric selection through all Layout measurement paths,
   ellipsis/wrap, completed text placement, Scene, SVG/PNG/PDF/Typst/TikZ, and
   raster font registration.
5. Specify a public evidence fixture whose table identifiers or source labels
   select the monospace role and proves measured width equals painted family.

## Required design outputs

1. An English design that gives the catalog data model, exact authority chain,
   resource migration, failure semantics, and exclusions.
2. An architecture review confirming that the catalog belongs above Layout,
   that Scene transports the selected identity only, and that no target infers
   or substitutes a family.
3. An implementation plan split into catalog closure, resource/corpus
   migration, and a release gate.  Each implementation slice must be
   independently materializable and publishable.

## Non-goals

- System-font use, arbitrary host fallbacks, or an unbounded CSS font stack.
- Adapter-owned measurement or font selection.
- A compatibility reader for a one-metric Context once the catalog schema is
  live.
- Adding discretionary display fonts or broadening the font catalog beyond the
  single functional monospace family required by #410.

## Design acceptance

The design is complete only when it proves that every measured text run uses
the exact asset selected by its Theme treatment; the same identity reaches
paint; one packaged monospace family is usable without import; immutable
Context/materializer reproducibility remains intact; and the primary wheel
budget remains enforceable.
