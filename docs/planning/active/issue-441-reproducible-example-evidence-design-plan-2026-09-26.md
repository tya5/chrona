# Design Plan — Reproducible Example Evidence and Reachability (#441)

## Problem

`examples/aster-ssd` still contains legacy slides, PNG previews, a gallery HTML
file, and four Views that no current corpus manifest materializes. The root
README hero points at one of those unowned previews, so it advertises stale
output rather than public evidence that Chrona can regenerate. A filesystem
glob in the View schema test also validates these unreachable files while
silently skipping older schema versions.

## Established facts

- `examples/aster-ssd/manifest.yaml` declares exactly one active slide,
  `overview`, with `generated/overview.svg` and `generated/overview.scene.json`
  as public materializer evidence.
- The README currently references
  `examples/aster-ssd/slides/04-qualification-production/preview.png`; neither
  that file nor `slides/`, `gallery.html`, or Views 02–05 is reachable from
  the active manifest.
- Public materializer reproduction has already passed for all declared corpus
  slides after the P0 visible-output work; the current generated ASTER SVG is
  suitable to become the README's honest hero evidence.
- Existing manifest/catalog tools enumerate declared slides but do not enforce
  that README image references are manifest evidence or that every tracked
  example file participates in a reachable closure.
- A View schema test currently globs `examples/**/views/*.yaml` and skips
  non-current versions, conflating filesystem presence with the declared
  public corpus.

## Questions

1. Which typed graph edges make a tracked example file reachable: manifest,
   selected Context, Context resource reference, recursively declared local
   source/asset reference, and generated evidence?
2. How does a README image reference prove it is the exact `expectedSvg` or
   another explicitly declared materializer artifact, instead of a copied
   preview with coincidentally similar bytes?
3. Which tracked supporting files are intentionally outside a render closure,
   and where is each such reason declared so an orphan cannot hide in a
   filesystem glob?
4. How should schema tests use the declared corpus population and fail a
   non-current View rather than skip it?

## Deliverables

- English design and whole-architecture review for source/evidence/reachability
  ownership.
- An implementation plan with a typed reachability checker, atomic ASTER
  cleanup and README migration, and checked generated inventory/release
  evidence.
- Removal of every legacy ASTER artifact and unrendered View named by #441.
- A deterministic gate for README evidence references and unreachable tracked
  example files.
